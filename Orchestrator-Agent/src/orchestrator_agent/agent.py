"""Orchestrator Agent — AI-powered full-stack development pipeline.

Wires up the MCP server, registers all tools, and exposes the
OrchestratorAgent class for single-shot and multi-turn usage.
"""

from __future__ import annotations

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    TextBlock,
    create_sdk_mcp_server,
)

from orchestrator_agent.system_prompt import SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Tool collection (lazy imports to avoid circular deps)
# ---------------------------------------------------------------------------

def _get_all_tools() -> list:
    from orchestrator_agent.tools.plan_project import plan_project
    from orchestrator_agent.tools.scaffold_project import scaffold_project
    from orchestrator_agent.tools.write_file import write_file
    from orchestrator_agent.tools.execute_command import execute_command
    from orchestrator_agent.tools.review_code import review_code
    from orchestrator_agent.tools.run_tests import run_tests
    from orchestrator_agent.tools.generate_docs import generate_docs
    from orchestrator_agent.tools.generate_deployment import generate_deployment
    return [
        plan_project,
        scaffold_project,
        write_file,
        execute_command,
        review_code,
        run_tests,
        generate_docs,
        generate_deployment,
    ]


# ---------------------------------------------------------------------------
# MCP server factory
# ---------------------------------------------------------------------------

def build_mcp_server():
    """Create and return the in-process MCP server."""
    return create_sdk_mcp_server(
        name="orchestrator",
        version="0.1.0",
        tools=_get_all_tools(),
    )


# ---------------------------------------------------------------------------
# Agent class
# ---------------------------------------------------------------------------

ALLOWED_TOOLS = [
    "mcp__orchestrator__plan_project",
    "mcp__orchestrator__scaffold_project",
    "mcp__orchestrator__write_file",
    "mcp__orchestrator__execute_command",
    "mcp__orchestrator__review_code",
    "mcp__orchestrator__run_tests",
    "mcp__orchestrator__generate_docs",
    "mcp__orchestrator__generate_deployment",
]


class OrchestratorAgent:
    """Full-Stack Orchestrator Agent."""

    def __init__(self) -> None:
        self._server = build_mcp_server()
        self._options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            mcp_servers={"orchestrator": self._server},
            allowed_tools=ALLOWED_TOOLS,
        )
        self._client = ClaudeSDKClient(self._options)

    # -- Single-shot query --------------------------------------------------
    def query(self, prompt: str) -> str:
        """Send a one-shot prompt and return the text response."""
        from claude_agent_sdk import query as sdk_query
        result = sdk_query(prompt, options=self._options)
        parts: list[str] = []
        for msg in result:
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        parts.append(block.text)
        return "\n".join(parts) if parts else "(no response)"

    # -- Multi-turn session -------------------------------------------------
    def run(self, prompt: str):
        """Start a multi-turn session and yield text chunks."""
        for event in self._client.stream(prompt):
            if isinstance(event, AssistantMessage):
                for block in event.content:
                    if isinstance(block, TextBlock):
                        yield block.text
