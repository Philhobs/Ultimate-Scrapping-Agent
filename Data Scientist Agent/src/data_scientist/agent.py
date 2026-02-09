"""DataScientistAgent — orchestrates end-to-end data analysis and ML workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console

from data_scientist.system_prompt import SYSTEM_PROMPT
from data_scientist import state

console = Console()


def _get_all_tools() -> list:
    """Import and return all MCP tool functions."""
    from data_scientist.tools.load_data import load_data
    from data_scientist.tools.inspect_data import inspect_data
    from data_scientist.tools.clean_data import clean_data
    from data_scientist.tools.engineer_features import engineer_features
    from data_scientist.tools.train_model import train_model
    from data_scientist.tools.evaluate_model import evaluate_model
    from data_scientist.tools.visualize import visualize
    from data_scientist.tools.report import report
    return [load_data, inspect_data, clean_data, engineer_features, train_model, evaluate_model, visualize, report]


TOOL_NAMES = [
    "mcp__ds__load_data",
    "mcp__ds__inspect_data",
    "mcp__ds__clean_data",
    "mcp__ds__engineer_features",
    "mcp__ds__train_model",
    "mcp__ds__evaluate_model",
    "mcp__ds__visualize",
    "mcp__ds__report",
]


class DataScientistAgent:
    """Main agent that handles data analysis and ML workflows."""

    def __init__(self, output_dir: str = "./output") -> None:
        self._output_dir = str(Path(output_dir).resolve())

    def initialize(self) -> None:
        """Set up shared state."""
        state.reset()
        state.set_output_dir(self._output_dir)
        Path(self._output_dir).mkdir(parents=True, exist_ok=True)
        console.print(f"[dim]Output directory: {self._output_dir}[/]")

    async def run(self, query: str, data_path: str | None = None, max_turns: int = 30) -> str:
        """Run a data science query through the Claude Agent SDK."""
        self.initialize()

        from claude_agent_sdk import (
            ClaudeSDKClient,
            ClaudeAgentOptions,
            AssistantMessage,
            TextBlock,
            create_sdk_mcp_server,
        )

        server = create_sdk_mcp_server(
            name="ds",
            version="1.0.0",
            tools=_get_all_tools(),
        )

        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            mcp_servers={"ds": server},
            allowed_tools=TOOL_NAMES,
            max_turns=max_turns,
        )

        # Build the full prompt
        if data_path:
            abs_path = str(Path(data_path).resolve())
            prompt = (
                f"I have a dataset at: {abs_path}\n\n"
                f"Task: {query}\n\n"
                f"Please load the data first, then proceed with the analysis."
            )
        else:
            prompt = query

        full_response: list[str] = []

        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            full_response.append(block.text)

        return "\n".join(full_response) if full_response else "No response generated."
