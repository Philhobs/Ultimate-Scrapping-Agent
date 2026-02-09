"""APIIntegratorAgent — orchestrates API calls and HuggingFace model inference."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rich.console import Console

from api_integrator.registry.api_registry import APIRegistry
from api_integrator.registry.model_registry import ModelRegistry
from api_integrator.system_prompt import SYSTEM_PROMPT
from api_integrator import state

console = Console()

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"


def _get_all_tools() -> list:
    """Import and return all MCP tool functions."""
    from api_integrator.tools.list_apis import list_apis
    from api_integrator.tools.register_api import register_api
    from api_integrator.tools.call_api import call_api
    from api_integrator.tools.search_models import search_models
    from api_integrator.tools.run_model import run_model
    from api_integrator.tools.chain_pipeline import chain_pipeline
    from api_integrator.tools.manage_results import manage_results
    return [list_apis, register_api, call_api, search_models, run_model, chain_pipeline, manage_results]


TOOL_NAMES = [
    "mcp__integrator__list_apis",
    "mcp__integrator__register_api",
    "mcp__integrator__call_api",
    "mcp__integrator__search_models",
    "mcp__integrator__run_model",
    "mcp__integrator__chain_pipeline",
    "mcp__integrator__manage_results",
]


class APIIntegratorAgent:
    """Main agent that handles API orchestration and HuggingFace model management."""

    def __init__(self) -> None:
        self._api_registry = APIRegistry()
        self._model_registry = ModelRegistry()
        self._initialized = False

    def initialize(self, config_path: str | None = None) -> None:
        """Load API registry from config and set shared state."""
        # Load default config
        default_config = CONFIG_DIR / "default_apis.yaml"
        if default_config.exists():
            self._api_registry.load_from_yaml(default_config)
            console.print(f"[dim]Loaded {len(self._api_registry.list_all())} APIs from default config[/]")

        # Load custom config if provided
        if config_path and Path(config_path).exists():
            self._api_registry.load_from_yaml(config_path)
            console.print(f"[dim]Loaded custom config: {config_path}[/]")

        # Set shared state for tools
        state.set_state(self._api_registry, self._model_registry)
        self._initialized = True

    async def run(self, query: str, max_turns: int = 25) -> str:
        """Run a query through the Claude Agent SDK with all tools available."""
        if not self._initialized:
            self.initialize()

        from claude_agent_sdk import (
            ClaudeSDKClient,
            ClaudeAgentOptions,
            AssistantMessage,
            TextBlock,
            create_sdk_mcp_server,
        )

        server = create_sdk_mcp_server(
            name="integrator",
            version="1.0.0",
            tools=_get_all_tools(),
        )

        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            mcp_servers={"integrator": server},
            allowed_tools=TOOL_NAMES,
            max_turns=max_turns,
        )

        full_response: list[str] = []

        async with ClaudeSDKClient(options=options) as client:
            await client.query(query)

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            full_response.append(block.text)

        return "\n".join(full_response) if full_response else "No response generated."

    async def run_pipeline(self, pipeline_config: dict[str, Any]) -> str:
        """Run a predefined pipeline from a YAML config."""
        if not self._initialized:
            self.initialize()

        description = pipeline_config.get("description", "Execute pipeline")
        steps = pipeline_config.get("steps", [])

        # Build a natural language prompt describing the pipeline
        step_descriptions = []
        for i, step in enumerate(steps, 1):
            step_descriptions.append(f"{i}. {step.get('description', step.get('type', 'unknown step'))}")

        prompt = (
            f"Execute this pipeline: {description}\n\n"
            f"Steps:\n" + "\n".join(step_descriptions) + "\n\n"
            f"Pipeline definition (use chain_pipeline tool with this):\n"
            f"```json\n{json.dumps(steps, indent=2)}\n```"
        )

        return await self.run(prompt)

    @property
    def api_registry(self) -> APIRegistry:
        return self._api_registry

    @property
    def model_registry(self) -> ModelRegistry:
        return self._model_registry
