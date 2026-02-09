"""RedTeamAgent — orchestrates security scanning, vulnerability testing, and defense evaluation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console

from redteam_agent.system_prompt import SYSTEM_PROMPT
from redteam_agent import state

console = Console()


def _get_all_tools() -> list:
    """Import and return all MCP tool functions."""
    from redteam_agent.tools.scan_target import scan_target
    from redteam_agent.tools.security_audit import security_audit
    from redteam_agent.tools.generate_payloads import generate_payloads
    from redteam_agent.tools.prompt_injection import prompt_injection
    from redteam_agent.tools.fuzz_inputs import fuzz_inputs
    from redteam_agent.tools.test_auth import test_auth
    from redteam_agent.tools.check_defenses import check_defenses
    from redteam_agent.tools.generate_report import generate_report
    return [
        scan_target,
        security_audit,
        generate_payloads,
        prompt_injection,
        fuzz_inputs,
        test_auth,
        check_defenses,
        generate_report,
    ]


TOOL_NAMES = [
    "mcp__redteam__scan_target",
    "mcp__redteam__security_audit",
    "mcp__redteam__generate_payloads",
    "mcp__redteam__prompt_injection",
    "mcp__redteam__fuzz_inputs",
    "mcp__redteam__test_auth",
    "mcp__redteam__check_defenses",
    "mcp__redteam__generate_report",
]


class RedTeamAgent:
    """Main agent that performs ethical security testing and red-team assessments."""

    def __init__(self) -> None:
        self._scanned = False

    def scan(self, path: str) -> dict[str, Any]:
        """Run local reconnaissance scan (no LLM needed)."""
        from redteam_agent.analyzers.vulnerability_scanner import scan_vulnerabilities

        console.print(f"[bold red]Scanning target:[/] {path}")

        # Quick vuln pre-scan
        findings = scan_vulnerabilities(path)
        state.set_findings(findings)
        self._scanned = True

        by_sev = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for f in findings:
            by_sev[f.severity] = by_sev.get(f.severity, 0) + 1

        console.print(f"  Findings: [red]{by_sev['critical']} critical[/], "
                      f"[yellow]{by_sev['high']} high[/], "
                      f"{by_sev['medium']} medium, {by_sev['low']} low")

        return {
            "total": len(findings),
            **by_sev,
        }

    async def run(self, query: str, target_path: str | None = None, max_turns: int = 30) -> str:
        """Run a query through the Claude Agent SDK with all tools."""
        from claude_agent_sdk import (
            ClaudeSDKClient,
            ClaudeAgentOptions,
            AssistantMessage,
            TextBlock,
            create_sdk_mcp_server,
        )

        server = create_sdk_mcp_server(
            name="redteam",
            version="1.0.0",
            tools=_get_all_tools(),
        )

        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            mcp_servers={"redteam": server},
            allowed_tools=TOOL_NAMES,
            max_turns=max_turns,
        )

        # Build prompt
        if target_path and not self._scanned:
            abs_path = str(Path(target_path).resolve())
            prompt = (
                f"First, scan the target at: {abs_path}\n\n"
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
