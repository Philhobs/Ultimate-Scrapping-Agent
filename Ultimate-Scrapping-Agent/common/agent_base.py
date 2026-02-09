"""Abstract base class for all Claude Agent SDK agents."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    create_sdk_mcp_server,
    query,
)

from common.config_loader import load_config


@dataclass
class AgentResult:
    """Structured result from an agent run."""

    messages: list[dict[str, Any]] = field(default_factory=list)
    text: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    cost_usd: float | None = None


class AgentBase(abc.ABC):
    """Abstract base class wrapping the Claude Agent SDK.

    Subclasses must implement:
        - `agent_name`: property returning the config file name
        - `system_prompt`: property returning the agent's system prompt
        - `get_tools()`: method returning a list of @tool-decorated functions
    """

    def __init__(self, config_overrides: dict[str, Any] | None = None) -> None:
        self.config = load_config(self.agent_name, overrides=config_overrides)
        agent_cfg = self.config.get("agent", {})
        self.model = agent_cfg.get("model", "claude-sonnet-4-5")
        self.max_turns = agent_cfg.get("max_turns", 15)

    @property
    @abc.abstractmethod
    def agent_name(self) -> str:
        """Config file name (without extension)."""

    @property
    @abc.abstractmethod
    def system_prompt(self) -> str:
        """System prompt for the agent."""

    @abc.abstractmethod
    def get_tools(self) -> list:
        """Return list of @tool-decorated async functions."""

    def _build_options(self) -> ClaudeAgentOptions:
        tools = self.get_tools()
        server = create_sdk_mcp_server(
            name=self.agent_name,
            version="1.0.0",
            tools=tools,
        )
        tool_names = [f"mcp__{self.agent_name}__{{}}".format(t.name) for t in tools]
        return ClaudeAgentOptions(
            system_prompt=self.system_prompt,
            model=self.model,
            max_turns=self.max_turns,
            mcp_servers={self.agent_name: server},
            allowed_tools=tool_names,
        )

    async def run(self, prompt: str) -> AgentResult:
        """Run the agent with the given prompt and return structured results."""
        options = self._build_options()
        result = AgentResult()
        text_parts: list[str] = []

        async for message in query(prompt=prompt, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        text_parts.append(block.text)
                        result.messages.append({"role": "assistant", "text": block.text})
                    elif isinstance(block, ToolUseBlock):
                        call_info = {
                            "tool": block.name,
                            "input": block.input,
                        }
                        result.tool_calls.append(call_info)
                        result.messages.append({"role": "tool_use", **call_info})
            elif isinstance(message, ResultMessage):
                if message.total_cost_usd:
                    result.cost_usd = message.total_cost_usd

        result.text = "\n".join(text_parts)
        return result
