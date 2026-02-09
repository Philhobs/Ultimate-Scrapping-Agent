"""CLI interface for API Integrator using Typer + Rich."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

app = typer.Typer(
    name="api-integrator",
    help="AI-powered API orchestrator & HuggingFace model hub agent.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def run(
    query: str = typer.Argument(help="Task or question for the agent"),
    config: str = typer.Option(None, "--config", "-c", help="Path to custom API config YAML"),
    max_turns: int = typer.Option(25, "--max-turns", "-m", help="Max agent turns"),
) -> None:
    """Run an interactive query — the agent will plan and execute API calls and model inferences."""
    from api_integrator.agent import APIIntegratorAgent

    agent = APIIntegratorAgent()
    agent.initialize(config_path=config)

    console.print(f"\n[bold blue]Query:[/] {query}\n")
    console.print("[dim]Planning and executing...[/]\n")

    answer = asyncio.run(agent.run(query, max_turns=max_turns))
    console.print(Markdown(answer))


@app.command()
def pipeline(
    config_file: str = typer.Argument(help="Path to pipeline YAML config"),
) -> None:
    """Execute a predefined pipeline from a YAML config file."""
    from api_integrator.agent import APIIntegratorAgent

    path = Path(config_file)
    if not path.exists():
        console.print(f"[red]Pipeline config not found: {config_file}[/]")
        raise typer.Exit(1)

    pipeline_config = yaml.safe_load(path.read_text())
    console.print(f"\n[bold blue]Pipeline:[/] {pipeline_config.get('name', path.stem)}")
    console.print(f"[dim]{pipeline_config.get('description', '')}[/]\n")

    agent = APIIntegratorAgent()
    agent.initialize()

    answer = asyncio.run(agent.run_pipeline(pipeline_config))
    console.print(Markdown(answer))


@app.command()
def apis(
    config: str = typer.Option(None, "--config", "-c", help="Path to custom API config YAML"),
) -> None:
    """List all registered APIs and their endpoints."""
    from api_integrator.agent import APIIntegratorAgent

    agent = APIIntegratorAgent()
    agent.initialize(config_path=config)

    apis_list = agent.api_registry.summary()

    if not apis_list:
        console.print("[yellow]No APIs registered.[/]")
        return

    for api in apis_list:
        table = Table(title=f"{api['name']} — {api['description']}", title_style="bold cyan")
        table.add_column("Endpoint", style="green")
        table.add_column("Method", style="yellow")
        table.add_column("Path")
        table.add_column("Description", style="dim")

        for ep in api.get("endpoints", []):
            table.add_row(ep["name"], ep["method"], ep["path"], ep["description"])

        console.print(table)
        console.print(f"  [dim]Base URL: {api['base_url']}  |  Auth: {api['auth_type']}[/]\n")


@app.command()
def models(
    task: str = typer.Option(None, "--task", "-t", help="Filter by task (e.g., summarization)"),
    query: str = typer.Option(None, "--query", "-q", help="Search by keyword"),
) -> None:
    """List available HuggingFace models by task or keyword."""
    from api_integrator.agent import APIIntegratorAgent

    agent = APIIntegratorAgent()
    registry = agent.model_registry

    if task:
        models_list = registry.get_models_for_task(task)
        if not models_list:
            console.print(f"[yellow]No models for task '{task}'.[/]")
            console.print(f"Available tasks: {', '.join(registry.get_tasks())}")
            return

        table = Table(title=f"Models for: {task}", title_style="bold cyan")
        table.add_column("Model ID", style="green")
        table.add_column("Description")
        table.add_column("Input", style="yellow")
        table.add_column("Output", style="yellow")

        for m in models_list:
            table.add_row(m.model_id, m.description, m.input_type, m.output_type)
        console.print(table)

    elif query:
        results = registry.search(query)
        if not results:
            console.print(f"[yellow]No models matching '{query}'.[/]")
            return

        table = Table(title=f"Search: {query}", title_style="bold cyan")
        table.add_column("Model ID", style="green")
        table.add_column("Task", style="yellow")
        table.add_column("Description")

        for m in results:
            table.add_row(m.model_id, m.task, m.description)
        console.print(table)

    else:
        # Show all tasks with model counts
        summary = registry.summary()
        table = Table(title="HuggingFace Model Registry", title_style="bold cyan")
        table.add_column("Task", style="green")
        table.add_column("Models", style="yellow", justify="right")
        table.add_column("Examples", style="dim")

        for entry in summary:
            examples = ", ".join(m["model_id"].split("/")[-1] for m in entry["models"][:2])
            table.add_row(entry["task"], str(entry["model_count"]), examples)

        console.print(table)
        console.print("\n[dim]Use --task <task> or --query <keyword> for details[/]")


def main() -> None:
    app()
