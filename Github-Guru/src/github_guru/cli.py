"""CLI interface for GitHub Guru using Typer + Rich."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

app = typer.Typer(
    name="github-guru",
    help="AI-powered GitHub repository analyzer.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def analyze(
    source: str = typer.Argument(help="Local path or GitHub URL to analyze"),
    no_embeddings: bool = typer.Option(False, "--no-embeddings", help="Skip embedding generation"),
) -> None:
    """Analyze a repository: parse structure, build dependency graph, compute embeddings."""
    from github_guru.agent import GitHubGuruAgent

    agent = GitHubGuruAgent()
    analysis = agent.analyze(source, no_embeddings=no_embeddings)

    # Display summary table
    table = Table(title="Analysis Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Repository", analysis.repo.name)
    table.add_row("Total Files", str(analysis.total_files))
    table.add_row("Total Lines", f"{analysis.total_lines:,}")

    # Top languages
    sorted_langs = sorted(analysis.languages.items(), key=lambda x: x[1], reverse=True)
    for lang, count in sorted_langs[:5]:
        table.add_row(f"  {lang}", str(count))

    total_classes = sum(len(f.classes) for f in analysis.files)
    total_functions = sum(
        len(f.functions) + sum(len(c.methods) for c in f.classes)
        for f in analysis.files
    )
    table.add_row("Classes", str(total_classes))
    table.add_row("Functions", str(total_functions))

    console.print(table)
    console.print(f"\n[dim]Cache saved to {analysis.repo.root_path}/.github-guru/[/]")


@app.command()
def ask(
    question: str = typer.Argument(help="Question to ask about the codebase"),
    repo: str = typer.Option(".", "--repo", "-r", help="Path to analyzed repository"),
) -> None:
    """Ask a question about an analyzed repository using AI."""
    from github_guru.agent import GitHubGuruAgent

    agent = GitHubGuruAgent()
    repo_path = str(Path(repo).resolve())

    if not agent.load_from_cache(repo_path):
        console.print("[yellow]No cached analysis found. Running analysis first...[/]")
        agent.analyze(repo_path)

    console.print(f"\n[bold blue]Question:[/] {question}\n")

    answer = asyncio.run(agent.ask(question))
    console.print(Markdown(answer))


@app.command()
def docs(
    source: str = typer.Argument(help="Local path or GitHub URL"),
    output: str = typer.Option("./docs", "-o", "--output", help="Output directory for docs"),
    doc_types: list[str] = typer.Option(
        None, "-t", "--type",
        help="Doc types to generate: overview, architecture, files, api",
    ),
) -> None:
    """Generate documentation for a repository."""
    from github_guru.agent import GitHubGuruAgent

    agent = GitHubGuruAgent()
    repo_path = str(Path(source).resolve())

    if not agent.load_from_cache(repo_path):
        console.print("[yellow]No cached analysis found. Running analysis first...[/]")
        agent.analyze(repo_path)

    generated = asyncio.run(agent.generate_docs(output, doc_types))

    if generated:
        console.print(f"\n[bold green]Generated {len(generated)} document(s):[/]")
        for path in generated:
            console.print(f"  [dim]{path}[/]")
    else:
        console.print("[yellow]No documents generated.[/]")


def main() -> None:
    app()
