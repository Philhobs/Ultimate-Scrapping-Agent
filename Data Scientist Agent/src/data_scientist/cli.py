"""CLI interface for Data Scientist Agent using Typer + Rich."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

app = typer.Typer(
    name="data-scientist",
    help="AI-powered data science agent with automated EDA, modeling, and reporting.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def analyze(
    data: str = typer.Argument(help="Path to dataset (CSV, JSON, Excel, Parquet)"),
    query: str = typer.Option(
        "Perform a complete data analysis: load the data, explore it, clean it, "
        "engineer features, train multiple models, evaluate them, create visualizations, "
        "and generate a full report with insights.",
        "--query", "-q",
        help="Analysis instructions",
    ),
    output: str = typer.Option("./output", "--output", "-o", help="Output directory for plots and reports"),
    max_turns: int = typer.Option(30, "--max-turns", "-m", help="Max agent turns"),
) -> None:
    """Run a full data analysis pipeline on a dataset."""
    from data_scientist.agent import DataScientistAgent

    path = Path(data)
    if not path.exists():
        console.print(f"[red]File not found: {data}[/]")
        raise typer.Exit(1)

    agent = DataScientistAgent(output_dir=output)

    console.print(f"\n[bold blue]Dataset:[/] {path.resolve()}")
    console.print(f"[bold blue]Task:[/] {query}\n")
    console.print("[dim]Running analysis...[/]\n")

    answer = asyncio.run(agent.run(query, data_path=str(path), max_turns=max_turns))
    console.print(Markdown(answer))


@app.command()
def explore(
    data: str = typer.Argument(help="Path to dataset"),
    output: str = typer.Option("./output", "--output", "-o", help="Output directory"),
) -> None:
    """Quick exploratory data analysis — summary stats, missing values, correlations, distributions."""
    from data_scientist.agent import DataScientistAgent

    path = Path(data)
    if not path.exists():
        console.print(f"[red]File not found: {data}[/]")
        raise typer.Exit(1)

    query = (
        "Load this dataset and perform exploratory data analysis:\n"
        "1. Show the data summary (shape, types, memory)\n"
        "2. Show descriptive statistics\n"
        "3. Check for missing values\n"
        "4. Show correlations between numeric columns\n"
        "5. Create a correlation heatmap\n"
        "6. Create histograms for key numeric columns\n"
        "7. Summarize your findings"
    )

    agent = DataScientistAgent(output_dir=output)
    console.print(f"\n[bold blue]Exploring:[/] {path.resolve()}\n")

    answer = asyncio.run(agent.run(query, data_path=str(path), max_turns=20))
    console.print(Markdown(answer))


@app.command()
def train(
    data: str = typer.Argument(help="Path to dataset"),
    target: str = typer.Option(..., "--target", "-t", help="Target column to predict"),
    task_type: str = typer.Option("auto", "--type", help="Task type: classification, regression, or auto"),
    output: str = typer.Option("./output", "--output", "-o", help="Output directory"),
    max_turns: int = typer.Option(30, "--max-turns", "-m", help="Max agent turns"),
) -> None:
    """Train ML models on a dataset, comparing multiple algorithms."""
    from data_scientist.agent import DataScientistAgent

    path = Path(data)
    if not path.exists():
        console.print(f"[red]File not found: {data}[/]")
        raise typer.Exit(1)

    task_hint = ""
    if task_type != "auto":
        task_hint = f"This is a {task_type} problem. "

    query = (
        f"Load this dataset and train models to predict '{target}'.\n"
        f"{task_hint}"
        "Steps:\n"
        "1. Load and explore the data\n"
        "2. Clean the data (handle missing values, encode categoricals)\n"
        "3. Engineer useful features if appropriate\n"
        "4. Train at least 3 different models with cross-validation\n"
        "5. Evaluate and compare all models\n"
        "6. Show feature importance for the best model\n"
        "7. Create relevant visualizations\n"
        "8. Generate a report with insights and model recommendations"
    )

    agent = DataScientistAgent(output_dir=output)
    console.print(f"\n[bold blue]Dataset:[/] {path.resolve()}")
    console.print(f"[bold blue]Target:[/] {target}")
    console.print(f"[bold blue]Type:[/] {task_type}\n")

    answer = asyncio.run(agent.run(query, data_path=str(path), max_turns=max_turns))
    console.print(Markdown(answer))


@app.command(name="report")
def generate_report(
    data: str = typer.Argument(help="Path to dataset"),
    query: str = typer.Option(
        "Analyze this dataset thoroughly and generate a comprehensive report.",
        "--query", "-q",
        help="Specific analysis question or focus area",
    ),
    output: str = typer.Option("./output", "--output", "-o", help="Output directory"),
) -> None:
    """Generate a comprehensive analysis report for a dataset."""
    from data_scientist.agent import DataScientistAgent

    path = Path(data)
    if not path.exists():
        console.print(f"[red]File not found: {data}[/]")
        raise typer.Exit(1)

    full_query = (
        f"{query}\n\n"
        "Make sure to:\n"
        "1. Explore the data thoroughly\n"
        "2. Create visualizations for key patterns\n"
        "3. If there's a clear target variable, train and compare models\n"
        "4. Generate a complete Markdown report with all findings and insights"
    )

    agent = DataScientistAgent(output_dir=output)
    console.print(f"\n[bold blue]Generating report for:[/] {path.resolve()}\n")

    answer = asyncio.run(agent.run(full_query, data_path=str(path), max_turns=30))
    console.print(Markdown(answer))


def main() -> None:
    app()
