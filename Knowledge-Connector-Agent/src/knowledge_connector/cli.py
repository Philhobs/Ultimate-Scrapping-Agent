"""CLI interface for Knowledge Connector Agent using Typer + Rich."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

app = typer.Typer(
    name="knowledge-connector",
    help="AI-powered document linker, consistency checker, and semantic search agent.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def index(
    path: str = typer.Argument(".", help="Directory to scan and index"),
) -> None:
    """Scan a directory and index all documents, building embeddings and a knowledge graph."""
    from knowledge_connector.agent import KnowledgeConnectorAgent

    resolved = str(Path(path).resolve())
    if not Path(resolved).is_dir():
        console.print(f"[red]Not a directory: {path}[/]")
        raise typer.Exit(1)

    agent = KnowledgeConnectorAgent()
    summary = agent.index(resolved)

    # Show top concepts
    if summary.get("top_concepts"):
        table = Table(title="Top Concepts", title_style="bold cyan")
        table.add_column("Concept", style="green")
        table.add_column("Mentioned In", style="yellow", justify="right")
        for tc in summary["top_concepts"][:10]:
            table.add_row(tc["concept"], str(tc["mentioned_in"]))
        console.print(table)


@app.command()
def search(
    query: str = typer.Argument(help="Search query"),
    path: str = typer.Option(".", "--path", "-p", help="Directory to search in"),
    top_k: int = typer.Option(5, "--top-k", "-k", help="Number of results"),
) -> None:
    """Semantic search across all documents in a directory."""
    from knowledge_connector.agent import KnowledgeConnectorAgent

    agent = KnowledgeConnectorAgent()
    resolved = str(Path(path).resolve())
    agent.index(resolved)

    full_query = (
        f"Search for: {query}\n\n"
        "Use the search tool and present the results clearly with source citations."
    )

    answer = asyncio.run(agent.run(full_query))
    console.print(Markdown(answer))


@app.command()
def check(
    path: str = typer.Argument(".", help="Directory to check"),
) -> None:
    """Check all documents for inconsistencies, broken links, and terminology divergence."""
    from knowledge_connector.agent import KnowledgeConnectorAgent

    agent = KnowledgeConnectorAgent()
    resolved = str(Path(path).resolve())
    agent.index(resolved)

    query = (
        "Check all indexed documents for consistency issues:\n"
        "1. Use check_consistency to find version mismatches, broken references, "
        "conflicting definitions, and terminology divergence.\n"
        "2. Use find_links on key documents to discover missing cross-references.\n"
        "3. Summarize all findings clearly."
    )

    answer = asyncio.run(agent.run(query))
    console.print(Markdown(answer))


@app.command()
def ask(
    question: str = typer.Argument(help="Question to ask about the knowledge base"),
    path: str = typer.Option(".", "--path", "-p", help="Directory containing documents"),
) -> None:
    """Ask a question and get an answer compiled from all relevant documents."""
    from knowledge_connector.agent import KnowledgeConnectorAgent

    agent = KnowledgeConnectorAgent()
    resolved = str(Path(path).resolve())
    agent.index(resolved)

    console.print(f"\n[bold blue]Question:[/] {question}\n")

    answer = asyncio.run(agent.run(question))
    console.print(Markdown(answer))


@app.command()
def graph(
    path: str = typer.Argument(".", help="Directory to analyze"),
) -> None:
    """Show the knowledge graph summary — concepts, relationships, and connections."""
    from knowledge_connector.agent import KnowledgeConnectorAgent

    agent = KnowledgeConnectorAgent()
    resolved = str(Path(path).resolve())
    summary = agent.index(resolved)

    console.print(f"\n[bold cyan]Knowledge Graph Summary[/]")
    console.print(f"  Documents: [green]{summary['total_documents']}[/]")
    console.print(f"  Concepts:  [green]{summary['total_concepts']}[/]")
    console.print(f"  Edges:     [green]{summary['total_edges']}[/]\n")

    if summary.get("top_concepts"):
        table = Table(title="Most Connected Concepts", title_style="bold cyan")
        table.add_column("Concept", style="green")
        table.add_column("Documents", style="yellow", justify="right")

        for tc in summary["top_concepts"]:
            table.add_row(tc["concept"], str(tc["mentioned_in"]))
        console.print(table)


def main() -> None:
    app()
