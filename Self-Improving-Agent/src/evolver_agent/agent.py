"""EvolverAgent — meta-agent that analyzes, evaluates, and improves other agents' prompts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console

from evolver_agent.system_prompt import SYSTEM_PROMPT
from evolver_agent import state

console = Console()


def _get_all_tools() -> list:
    """Import and return all MCP tool functions."""
    from evolver_agent.tools.analyze_agent import analyze_agent
    from evolver_agent.tools.evaluate_prompt import evaluate_prompt
    from evolver_agent.tools.generate_variant import generate_variant
    from evolver_agent.tools.run_experiment import run_experiment
    from evolver_agent.tools.apply_improvement import apply_improvement
    from evolver_agent.tools.track_metrics import track_metrics
    from evolver_agent.tools.rollback import rollback
    from evolver_agent.tools.generate_report import generate_report
    return [
        analyze_agent,
        evaluate_prompt,
        generate_variant,
        run_experiment,
        apply_improvement,
        track_metrics,
        rollback,
        generate_report,
    ]


TOOL_NAMES = [
    "mcp__evolver__analyze_agent",
    "mcp__evolver__evaluate_prompt",
    "mcp__evolver__generate_variant",
    "mcp__evolver__run_experiment",
    "mcp__evolver__apply_improvement",
    "mcp__evolver__track_metrics",
    "mcp__evolver__rollback",
    "mcp__evolver__generate_report",
]


class EvolverAgent:
    """Meta-agent that evolves other agents through prompt optimization."""

    def __init__(self) -> None:
        self._analyzed = False

    def quick_profile(self, path: str) -> dict[str, Any]:
        """Quick profile of a target agent (no LLM needed)."""
        from evolver_agent.analyzers.evaluator import evaluate_prompt
        from evolver_agent.analyzers.prompt_evolver import analyze_prompt_structure
        import re

        root = Path(path).resolve()
        console.print(f"[bold magenta]Profiling agent:[/] {root.name}")

        # Find and read system prompt
        prompt_content = ""
        for candidate in root.rglob("system_prompt.py"):
            raw = candidate.read_text(errors="replace")
            match = re.search(r'SYSTEM_PROMPT\s*=\s*(?:"""|\'\'\'|"")(.*?)(?:"""|\'\'\'|"")', raw, re.DOTALL)
            if match:
                prompt_content = match.group(1)
            break

        if not prompt_content:
            console.print("[yellow]  No system_prompt.py found[/]")
            return {"name": root.name, "error": "no system prompt found"}

        scores = evaluate_prompt(prompt_content)
        structure = analyze_prompt_structure(prompt_content)

        console.print(f"  Overall Score: [{'green' if scores.overall >= 70 else 'yellow' if scores.overall >= 50 else 'red'}]{scores.overall:.0f}/100[/]")
        console.print(f"  Clarity:       {scores.clarity:.0f}  |  Safety:    {scores.safety:.0f}")
        console.print(f"  Structure:     {scores.structure:.0f}  |  Efficiency: {scores.efficiency:.0f}")
        console.print(f"  Completeness:  {scores.completeness:.0f}  |  Specificity: {scores.specificity:.0f}")
        console.print(f"  Tokens:        ~{structure['estimated_tokens']}")

        return {
            "name": root.name,
            "scores": scores.to_dict(),
            "tokens": structure["estimated_tokens"],
        }

    async def run(self, query: str, agent_path: str | None = None, max_turns: int = 35) -> str:
        """Run a query through the Claude Agent SDK with all tools."""
        from claude_agent_sdk import (
            ClaudeSDKClient,
            ClaudeAgentOptions,
            AssistantMessage,
            TextBlock,
            create_sdk_mcp_server,
        )

        server = create_sdk_mcp_server(
            name="evolver",
            version="1.0.0",
            tools=_get_all_tools(),
        )

        options = ClaudeAgentOptions(
            system_prompt=SYSTEM_PROMPT,
            mcp_servers={"evolver": server},
            allowed_tools=TOOL_NAMES,
            max_turns=max_turns,
        )

        # Build prompt
        if agent_path and not self._analyzed:
            abs_path = str(Path(agent_path).resolve())
            prompt = (
                f"First, analyze the agent at: {abs_path}\n\n"
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
