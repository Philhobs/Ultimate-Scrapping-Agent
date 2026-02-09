"""CLI interface for Self-Improving Recursive Agent using Typer + Rich."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

app = typer.Typer(
    name="evolver-agent",
    help="AI-powered self-improving agent: evolve system prompts, run experiments, track improvements.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def evolve(
    path: str = typer.Argument(help="Path to the target agent's directory"),
    strategy: str = typer.Option(None, "--strategy", "-s", help="Mutation strategy to apply"),
    output: str = typer.Option("./evolver-output", "--output", "-o", help="Output directory"),
) -> None:
    """Full evolution cycle: analyze, evaluate, generate variant, experiment, and apply."""
    from evolver_agent.agent import EvolverAgent
    from evolver_agent import state

    resolved = str(Path(path).resolve())
    if not Path(resolved).is_dir():
        console.print(f"[red]Not a directory: {path}[/]")
        raise typer.Exit(1)

    state.set_output_dir(str(Path(output).resolve()))
    agent = EvolverAgent()
    agent.quick_profile(resolved)

    console.print(f"\n[bold magenta]Running evolution cycle...[/]\n")

    strategy_str = f" Use the '{strategy}' strategy." if strategy else ""
    query = (
        f"I've profiled the agent. Now do a full evolution cycle:\n"
        "1. analyze_agent to deeply understand the current prompt\n"
        "2. evaluate_prompt to baseline the current score\n"
        f"3. generate_variant — pick the best mutation strategy for weaknesses found{strategy_str}\n"
        "   (You must rewrite the prompt yourself applying the strategy, then store it)\n"
        "4. run_experiment comparing baseline vs variant\n"
        "5. If the variant wins, apply_improvement\n"
        "6. track_metrics and save\n"
        "7. generate_report documenting the evolution\n\n"
        "Explain every change you make and why it should improve the prompt."
    )

    answer = asyncio.run(agent.run(query))
    console.print(Markdown(answer))


@app.command()
def profile(
    path: str = typer.Argument(help="Path to the target agent's directory"),
) -> None:
    """Analyze and score an agent's system prompt."""
    from evolver_agent.agent import EvolverAgent

    resolved = str(Path(path).resolve())
    if not Path(resolved).is_dir():
        console.print(f"[red]Not a directory: {path}[/]")
        raise typer.Exit(1)

    agent = EvolverAgent()

    console.print(f"\n[bold magenta]Deep analysis...[/]\n")

    query = (
        f"Analyze the agent at {resolved} in depth. "
        "Show the full scorecard, structural analysis, "
        "and recommend specific improvements with their expected impact."
    )

    answer = asyncio.run(agent.run(query, agent_path=resolved))
    console.print(Markdown(answer))


@app.command()
def compare(
    agent_a: str = typer.Argument(help="Path to first agent"),
    agent_b: str = typer.Argument(help="Path to second agent"),
) -> None:
    """Compare two agents' system prompts side by side."""
    from evolver_agent.agent import EvolverAgent

    resolved_a = str(Path(agent_a).resolve())
    resolved_b = str(Path(agent_b).resolve())

    agent = EvolverAgent()

    console.print(f"\n[bold magenta]Comparing agents...[/]\n")

    # Quick profile both
    info_a = agent.quick_profile(resolved_a)
    console.print()
    info_b = agent.quick_profile(resolved_b)

    # Show comparison table
    table = Table(title="Agent Comparison", title_style="bold magenta")
    table.add_column("Dimension", style="cyan")
    table.add_column(info_a.get("name", "Agent A"), style="green")
    table.add_column(info_b.get("name", "Agent B"), style="yellow")

    scores_a = info_a.get("scores", {})
    scores_b = info_b.get("scores", {})
    for dim in ("clarity", "completeness", "structure", "specificity", "safety", "efficiency", "overall"):
        va = scores_a.get(dim, 0)
        vb = scores_b.get(dim, 0)
        table.add_row(dim.title(), f"{va:.1f}", f"{vb:.1f}")
    console.print(table)


@app.command()
def batch_profile(
    path: str = typer.Argument(".", help="Parent directory containing agent folders"),
) -> None:
    """Profile all agents in a parent directory."""
    from evolver_agent.agent import EvolverAgent

    root = Path(path).resolve()
    agent = EvolverAgent()

    results: list[dict] = []
    for child in sorted(root.iterdir()):
        if child.is_dir() and any(child.rglob("system_prompt.py")):
            info = agent.quick_profile(str(child))
            results.append(info)
            console.print()

    if results:
        table = Table(title="Agent Fleet Scorecard", title_style="bold magenta")
        table.add_column("Agent", style="cyan")
        table.add_column("Overall", style="green", justify="right")
        table.add_column("Clarity", justify="right")
        table.add_column("Safety", justify="right")
        table.add_column("Structure", justify="right")
        table.add_column("Tokens", justify="right")

        for r in sorted(results, key=lambda x: x.get("scores", {}).get("overall", 0), reverse=True):
            s = r.get("scores", {})
            table.add_row(
                r.get("name", "?"),
                f"{s.get('overall', 0):.0f}",
                f"{s.get('clarity', 0):.0f}",
                f"{s.get('safety', 0):.0f}",
                f"{s.get('structure', 0):.0f}",
                str(r.get("tokens", "?")),
            )
        console.print(table)


@app.command()
def rollback_cmd(
    path: str = typer.Argument(help="Path to the target agent's directory"),
    version: int = typer.Option(0, "--version", "-v", help="Version ID to revert to"),
) -> None:
    """Revert an agent's prompt to a previous version."""
    from evolver_agent.agent import EvolverAgent

    resolved = str(Path(path).resolve())
    agent = EvolverAgent()

    console.print(f"\n[bold magenta]Rolling back to version {version}...[/]\n")

    query = (
        f"Analyze the agent at {resolved}, then rollback to version {version}. "
        "Show what changed and confirm the rollback was successful."
    )

    answer = asyncio.run(agent.run(query, agent_path=resolved))
    console.print(Markdown(answer))


@app.command()
def ask(
    question: str = typer.Argument(help="Question about agent optimization"),
    path: str = typer.Option(None, "--path", "-p", help="Path to an agent directory"),
    output: str = typer.Option("./evolver-output", "--output", "-o", help="Output directory"),
) -> None:
    """Ask any question about agent optimization and prompt engineering."""
    from evolver_agent.agent import EvolverAgent
    from evolver_agent import state

    state.set_output_dir(str(Path(output).resolve()))
    agent = EvolverAgent()

    console.print(f"\n[bold magenta]Question:[/] {question}\n")

    answer = asyncio.run(agent.run(question, agent_path=path))
    console.print(Markdown(answer))


def main() -> None:
    app()
