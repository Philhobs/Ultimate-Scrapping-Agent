"""TestingAgent — orchestrates test generation, execution, debugging, and fixing."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console

from testing_agent.system_prompt import SYSTEM_PROMPT
from testing_agent import state

console = Console()


def _get_all_tools() -> list:
    """Import and return all MCP tool functions."""
    from testing_agent.tools.analyze_codebase import analyze_codebase
    from testing_agent.tools.read_source import read_source
    from testing_agent.tools.generate_tests import generate_tests
    from testing_agent.tools.run_tests import run_tests
    from testing_agent.tools.debug_failure import debug_failure
    from testing_agent.tools.apply_fix import apply_fix
    from testing_agent.tools.check_coverage import check_coverage
    from testing_agent.tools.profile_performance import profile_performance
    return [
        analyze_codebase,
        read_source,
        generate_tests,
        run_tests,
        debug_failure,
        apply_fix,
        check_coverage,
        profile_performance,
    ]


TOOL_NAMES = [
    "mcp__testing__analyze_codebase",
    "mcp__testing__read_source",
    "mcp__testing__generate_tests",
    "mcp__testing__run_tests",
    "mcp__testing__debug_failure",
    "mcp__testing__apply_fix",
    "mcp__testing__check_coverage",
    "mcp__testing__profile_performance",
]


class TestingAgent:
    """Main agent that handles testing, debugging, and code quality."""

    def __init__(self) -> None:
        self._analyzed = False

    def analyze(self, path: str) -> dict[str, Any]:
        """Run local codebase analysis (no LLM needed)."""
        from testing_agent.analyzers.code_parser import scan_codebase

        console.print(f"[bold blue]Scanning:[/] {path}")
        profile = scan_codebase(path)
        state.set_profile(profile)
        self._analyzed = True

        console.print(f"  Language:       [green]{profile.language}[/]")
        console.print(f"  Test Framework: [green]{profile.test_framework or 'None detected'}[/]")
        console.print(f"  Source Files:   [green]{len(profile.source_files)}[/]")
        console.print(f"  Test Files:     {'[green]' + str(len(profile.test_files)) if profile.test_files else '[yellow]0'}[/]")
        console.print(f"  Functions:      [green]{profile.total_functions}[/]")
        console.print(f"  Total Lines:    [green]{profile.total_lines:,}[/]")

        return {
            "name": profile.name,
            "language": profile.language,
            "test_framework": profile.test_framework,
            "source_files": len(profile.source_files),
            "test_files": len(profile.test_files),
            "functions": profile.total_functions,
            "total_lines": profile.total_lines,
        }

    async def run(self, query: str, project_path: str | None = None, max_turns: int = 30) -> str:
        """Run a query through the Claude Agent SDK with all tools."""
        from claude_agent_sdk import (
            ClaudeSDKClient,
            ClaudeAgentOptions,
            AssistantMessage,
            TextBlock,
            create_sdk_mcp_server,
        )

        server = create_sdk_mcp_server(
            name="testing",
            version="1.0.0",
            tools=_get_all_tools(),
        )

        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            mcp_servers={"testing": server},
            allowed_tools=TOOL_NAMES,
            max_turns=max_turns,
        )

        # Build prompt
        if project_path and not self._analyzed:
            abs_path = str(Path(project_path).resolve())
            prompt = (
                f"First, analyze the codebase at: {abs_path}\n\n"
                f"Then: {query}"
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
