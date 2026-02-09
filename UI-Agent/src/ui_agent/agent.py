"""UIAgent — orchestrates UI design analysis and frontend code generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console

from ui_agent.system_prompt import SYSTEM_PROMPT
from ui_agent import state

console = Console()


def _get_all_tools() -> list:
    """Import and return all MCP tool functions."""
    from ui_agent.tools.read_image import read_image
    from ui_agent.tools.generate_ui_spec import generate_ui_spec
    from ui_agent.tools.generate_component import generate_component
    from ui_agent.tools.generate_page import generate_page
    from ui_agent.tools.refine_design import refine_design
    from ui_agent.tools.generate_style_guide import generate_style_guide
    from ui_agent.tools.export_code import export_code
    from ui_agent.tools.read_file import read_file
    return [
        read_image,
        generate_ui_spec,
        generate_component,
        generate_page,
        refine_design,
        generate_style_guide,
        export_code,
        read_file,
    ]


TOOL_NAMES = [
    "mcp__ui__read_image",
    "mcp__ui__generate_ui_spec",
    "mcp__ui__generate_component",
    "mcp__ui__generate_page",
    "mcp__ui__refine_design",
    "mcp__ui__generate_style_guide",
    "mcp__ui__export_code",
    "mcp__ui__read_file",
]


class UIAgent:
    """Main agent that generates UI code from descriptions and screenshots."""

    def __init__(self) -> None:
        self._analyzed = False

    def analyze(self, path: str) -> dict[str, Any]:
        """Run local project analysis for existing UI structure (no LLM needed)."""
        from ui_agent.analyzers.design_scanner import scan_project

        console.print(f"[bold blue]Scanning:[/] {path}")
        profile = scan_project(path)
        state.set_profile(profile)
        self._analyzed = True

        console.print(f"  Project:    [green]{profile.name}[/]")
        console.print(f"  Files:      [green]{profile.file_count}[/]")
        console.print(f"  CSS:        {'[green]' + profile.css_framework if profile.has_css_framework else '[yellow]None detected'}[/]")
        console.print(f"  Tailwind:   {'[green]Yes' if profile.has_tailwind else '[yellow]No'}[/]")
        console.print(f"  React:      {'[green]Yes' if profile.has_react else '[yellow]No'}[/]")
        console.print(f"  Components: {'[green]' + str(len(profile.component_files)) if profile.has_components else '[yellow]None'}[/]")
        console.print(f"  Pages:      [green]{len(profile.existing_pages)}[/]")

        return profile.to_dict()

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
            name="ui",
            version="1.0.0",
            tools=_get_all_tools(),
        )

        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            mcp_servers={"ui": server},
            allowed_tools=TOOL_NAMES,
            max_turns=max_turns,
        )

        # Build prompt with context
        parts: list[str] = []

        if project_path and not self._analyzed:
            abs_path = str(Path(project_path).resolve())
            self.analyze(abs_path)

        profile = state.get_profile()
        if profile:
            parts.append(
                f"Project context: {profile.name} "
                f"(CSS: {profile.css_framework or 'none'}, "
                f"React: {profile.has_react}, "
                f"Tailwind: {profile.has_tailwind})"
            )

        parts.append(query)
        prompt = "\n\n".join(parts)

        full_response: list[str] = []

        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            full_response.append(block.text)

        return "\n".join(full_response) if full_response else "No response generated."
