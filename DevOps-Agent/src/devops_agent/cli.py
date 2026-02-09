"""CLI interface for DevOps Agent using Typer + Rich."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

app = typer.Typer(
    name="devops-agent",
    help="AI-powered DevOps engineer: Dockerfiles, CI/CD, infrastructure, security scanning.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def setup(
    path: str = typer.Argument(".", help="Project directory to analyze"),
    output: str = typer.Option("./devops-output", "--output", "-o", help="Output directory for generated files"),
) -> None:
    """Full DevOps setup: analyze, scan, generate Dockerfile, CI/CD, infra, and report."""
    from devops_agent.agent import DevOpsAgent
    from devops_agent import state

    resolved = str(Path(path).resolve())
    if not Path(resolved).is_dir():
        console.print(f"[red]Not a directory: {path}[/]")
        raise typer.Exit(1)

    state.set_output_dir(str(Path(output).resolve()))
    agent = DevOpsAgent()
    agent.analyze(resolved)

    console.print(f"\n[bold cyan]Running full DevOps setup...[/]\n")

    query = (
        f"I've already analyzed the project at {resolved}. Now do a full DevOps setup:\n"
        "1. Run security_scan to check for vulnerabilities\n"
        "2. Generate a Dockerfile (with compose)\n"
        "3. Generate GitHub Actions CI/CD pipeline\n"
        "4. Generate Kubernetes manifests\n"
        "5. Generate a Makefile for convenience\n"
        "6. Check deployment health/readiness\n"
        "7. Generate the final DevOps report with your recommendations\n\n"
        "Explain each step and your choices."
    )

    answer = asyncio.run(agent.run(query))
    console.print(Markdown(answer))


@app.command()
def scan(
    path: str = typer.Argument(".", help="Project directory to scan"),
) -> None:
    """Analyze a project and show its DevOps profile."""
    from devops_agent.agent import DevOpsAgent

    resolved = str(Path(path).resolve())
    if not Path(resolved).is_dir():
        console.print(f"[red]Not a directory: {path}[/]")
        raise typer.Exit(1)

    agent = DevOpsAgent()
    info = agent.analyze(resolved)

    table = Table(title="Project Profile", title_style="bold cyan")
    table.add_column("Property", style="green")
    table.add_column("Value", style="white")
    for key, val in info.items():
        table.add_row(key.replace("_", " ").title(), str(val))
    console.print(table)


@app.command()
def security(
    path: str = typer.Argument(".", help="Project directory to scan"),
) -> None:
    """Run a security scan and show findings."""
    from devops_agent.agent import DevOpsAgent
    from devops_agent import state

    resolved = str(Path(path).resolve())
    agent = DevOpsAgent()
    agent.analyze(resolved)

    console.print(f"\n[bold cyan]Running security scan...[/]\n")

    query = (
        f"Run security_scan on the project at {resolved}. "
        "Present all findings grouped by severity, with clear remediation advice."
    )

    answer = asyncio.run(agent.run(query))
    console.print(Markdown(answer))


@app.command()
def dockerize(
    path: str = typer.Argument(".", help="Project directory"),
    output: str = typer.Option("./devops-output", "--output", "-o", help="Output directory"),
    compose: bool = typer.Option(False, "--compose", "-c", help="Also generate docker-compose.yml"),
) -> None:
    """Generate a Dockerfile (and optionally docker-compose) for the project."""
    from devops_agent.agent import DevOpsAgent
    from devops_agent import state

    resolved = str(Path(path).resolve())
    state.set_output_dir(str(Path(output).resolve()))

    agent = DevOpsAgent()
    agent.analyze(resolved)

    console.print(f"\n[bold cyan]Generating Dockerfile...[/]\n")

    compose_str = " with compose=true" if compose else ""
    query = (
        f"Generate a production-ready Dockerfile{compose_str} for this project. "
        "Explain your choices for base image, build stages, and security practices."
    )

    answer = asyncio.run(agent.run(query))
    console.print(Markdown(answer))


@app.command()
def pipeline(
    path: str = typer.Argument(".", help="Project directory"),
    platform: str = typer.Option("github_actions", "--platform", "-p", help="CI platform: github_actions, gitlab_ci, jenkinsfile"),
    output: str = typer.Option("./devops-output", "--output", "-o", help="Output directory"),
) -> None:
    """Generate a CI/CD pipeline configuration."""
    from devops_agent.agent import DevOpsAgent
    from devops_agent import state

    resolved = str(Path(path).resolve())
    state.set_output_dir(str(Path(output).resolve()))

    agent = DevOpsAgent()
    agent.analyze(resolved)

    console.print(f"\n[bold cyan]Generating {platform} pipeline...[/]\n")

    query = (
        f"Generate a {platform} CI/CD pipeline for this project. "
        "Include build, test, lint, security scan, and deploy stages. "
        "Explain the pipeline structure and your choices."
    )

    answer = asyncio.run(agent.run(query))
    console.print(Markdown(answer))


@app.command()
def ask(
    question: str = typer.Argument(help="DevOps question about your project"),
    path: str = typer.Option(".", "--path", "-p", help="Project directory"),
    output: str = typer.Option("./devops-output", "--output", "-o", help="Output directory"),
) -> None:
    """Ask any DevOps question about your project."""
    from devops_agent.agent import DevOpsAgent
    from devops_agent import state

    resolved = str(Path(path).resolve())
    state.set_output_dir(str(Path(output).resolve()))

    agent = DevOpsAgent()

    console.print(f"\n[bold blue]Question:[/] {question}\n")

    answer = asyncio.run(agent.run(question, project_path=resolved))
    console.print(Markdown(answer))


def main() -> None:
    app()
