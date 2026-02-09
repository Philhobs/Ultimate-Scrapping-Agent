"""DevOpsAgent — orchestrates project analysis, security, and deployment config generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console

from devops_agent.system_prompt import SYSTEM_PROMPT
from devops_agent import state

console = Console()


def _get_all_tools() -> list:
    """Import and return all MCP tool functions."""
    from devops_agent.tools.analyze_project import analyze_project
    from devops_agent.tools.generate_dockerfile import generate_dockerfile
    from devops_agent.tools.generate_ci_cd import generate_ci_cd
    from devops_agent.tools.generate_infrastructure import generate_infrastructure
    from devops_agent.tools.security_scan import security_scan
    from devops_agent.tools.generate_deploy_script import generate_deploy_script
    from devops_agent.tools.check_health import check_health
    from devops_agent.tools.generate_report import generate_report
    return [
        analyze_project,
        generate_dockerfile,
        generate_ci_cd,
        generate_infrastructure,
        security_scan,
        generate_deploy_script,
        check_health,
        generate_report,
    ]


TOOL_NAMES = [
    "mcp__devops__analyze_project",
    "mcp__devops__generate_dockerfile",
    "mcp__devops__generate_ci_cd",
    "mcp__devops__generate_infrastructure",
    "mcp__devops__security_scan",
    "mcp__devops__generate_deploy_script",
    "mcp__devops__check_health",
    "mcp__devops__generate_report",
]


class DevOpsAgent:
    """Main agent that analyzes projects and generates DevOps configs."""

    def __init__(self) -> None:
        self._analyzed = False

    def analyze(self, path: str) -> dict[str, Any]:
        """Run local project analysis (no LLM needed)."""
        from devops_agent.analyzers.project_scanner import scan_project

        console.print(f"[bold blue]Scanning:[/] {path}")
        profile = scan_project(path)
        state.set_profile(profile)
        self._analyzed = True

        console.print(f"  Language:  [green]{profile.language}[/]")
        console.print(f"  Framework: [green]{profile.framework or 'None detected'}[/]")
        console.print(f"  Files:     [green]{profile.file_count}[/]")
        console.print(f"  Lines:     [green]{profile.total_lines:,}[/]")
        console.print(f"  Docker:    {'[green]Yes' if profile.has_docker else '[yellow]No'}[/]")
        console.print(f"  CI/CD:     {'[green]Yes' if profile.has_ci else '[yellow]No'}[/]")
        console.print(f"  Tests:     {'[green]Yes' if profile.has_tests else '[yellow]No'}[/]")

        return {
            "name": profile.name,
            "language": profile.language,
            "framework": profile.framework,
            "file_count": profile.file_count,
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
            name="devops",
            version="1.0.0",
            tools=_get_all_tools(),
        )

        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            mcp_servers={"devops": server},
            allowed_tools=TOOL_NAMES,
            max_turns=max_turns,
        )

        # Build prompt
        if project_path and not self._analyzed:
            abs_path = str(Path(project_path).resolve())
            prompt = (
                f"First, analyze the project at: {abs_path}\n\n"
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
