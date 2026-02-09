"""CLI for the Orchestrator Agent.

Commands:
  build    — Full project build from a description
  plan     — Generate a project plan only
  scaffold — Scaffold from an existing plan
  review   — Code review on generated files
  deploy   — Generate deployment configs
  ask      — Free-form question to the agent
"""

from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.markdown import Markdown

app = typer.Typer(
    name="orchestrator-agent",
    help="AI-powered full-stack development pipeline — idea to deployment.",
    no_args_is_help=True,
)
console = Console()


# ---------------------------------------------------------------------------
# build — Full project build
# ---------------------------------------------------------------------------

@app.command()
def build(
    description: str = typer.Argument(..., help="Project description / requirements"),
    name: str = typer.Option("my-project", "--name", "-n", help="Project name"),
    output: str = typer.Option("./orchestrator-output", "--output", "-o", help="Output directory"),
):
    """Build a full project from idea to deployment-ready code."""
    from orchestrator_agent import state
    state.set_output_dir(output)

    from orchestrator_agent.agent import OrchestratorAgent
    agent = OrchestratorAgent()

    prompt = (
        f"Build a complete project from this description:\n\n"
        f"Project name: {name}\n"
        f"Description: {description}\n\n"
        f"Follow the Full Project Build workflow:\n"
        f"1. plan_project\n"
        f"2. scaffold_project\n"
        f"3. write_file for each module\n"
        f"4. run_tests\n"
        f"5. review_code\n"
        f"6. Fix any issues\n"
        f"7. generate_docs\n"
        f"8. generate_deployment\n"
    )

    console.print(f"\n[bold cyan]Building project: {name}[/bold cyan]\n")
    for chunk in agent.run(prompt):
        console.print(Markdown(chunk))


# ---------------------------------------------------------------------------
# plan — Just the planning phase
# ---------------------------------------------------------------------------

@app.command()
def plan(
    description: str = typer.Argument(..., help="Project description"),
    name: str = typer.Option("my-project", "--name", "-n", help="Project name"),
):
    """Generate a project plan without building."""
    from orchestrator_agent.analyzers.project_planner import create_project_plan
    plan_data = create_project_plan(description, name)

    console.print(f"\n[bold cyan]Project Plan: {name}[/bold cyan]\n")
    console.print(f"[bold]Type:[/bold] {plan_data['project_type']}")
    console.print(f"[bold]Language:[/bold] {plan_data['language']}")
    console.print(f"[bold]Preset:[/bold] {plan_data['preset']}\n")

    console.print("[bold]Tech Stack:[/bold]")
    for cat, items in plan_data["tech_stack"].items():
        console.print(f"  {cat}: {', '.join(items)}")

    console.print(f"\n[bold]File Structure ({len(plan_data['file_structure'])} files):[/bold]")
    for f in plan_data["file_structure"]:
        console.print(f"  {f}")

    console.print(f"\n[bold]Milestones:[/bold]")
    for m in plan_data["milestones"]:
        console.print(f"  Phase {m['phase']}: {m['name']} — {m['description']}")

    console.print()


# ---------------------------------------------------------------------------
# scaffold — Create project structure
# ---------------------------------------------------------------------------

@app.command()
def scaffold(
    description: str = typer.Argument(..., help="Project description"),
    name: str = typer.Option("my-project", "--name", "-n", help="Project name"),
    output: str = typer.Option("./orchestrator-output", "--output", "-o", help="Output directory"),
):
    """Scaffold a project directory from a description."""
    from orchestrator_agent import state
    from orchestrator_agent.analyzers.project_planner import create_project_plan
    from orchestrator_agent.tools.scaffold_project import scaffold_project

    plan_data = create_project_plan(description, name)
    state.set_plan(plan_data)
    state.set_output_dir(output)

    result = scaffold_project(output)
    text = result["content"][0]["text"]
    console.print(f"\n[bold cyan]Scaffold[/bold cyan]\n")
    console.print(text)
    console.print()


# ---------------------------------------------------------------------------
# review — Code review
# ---------------------------------------------------------------------------

@app.command()
def review(
    path: str = typer.Argument(".", help="Directory to review"),
):
    """Run code review on files in a directory."""
    import os
    from pathlib import Path
    from orchestrator_agent.analyzers.code_reviewer import review_project

    files: dict[str, str] = {}
    root = Path(path)
    for ext in ("*.py", "*.js", "*.ts", "*.tsx", "*.go"):
        for fpath in root.rglob(ext):
            rel = str(fpath.relative_to(root))
            try:
                files[rel] = fpath.read_text()
            except Exception:
                pass

    if not files:
        console.print("[yellow]No source files found.[/yellow]")
        raise typer.Exit()

    report = review_project(files)
    console.print(f"\n[bold cyan]Code Review — {report['total_files_reviewed']} files[/bold cyan]\n")
    console.print(f"  Critical: [red]{report['critical']}[/red]")
    console.print(f"  Warnings: [yellow]{report['warnings']}[/yellow]")
    console.print(f"  Info:     [blue]{report['info']}[/blue]")

    if report["passed"]:
        console.print("\n  [bold green]PASSED[/bold green]\n")
    else:
        console.print("\n  [bold red]FAILED — fix critical issues[/bold red]\n")

    for f in report["findings"][:30]:
        color = {"critical": "red", "warning": "yellow", "info": "blue"}.get(f["severity"], "white")
        console.print(f"  [{color}][{f['severity'].upper()}][/{color}] {f['file']}:{f['line']} — {f['message']}")
        if f.get("suggestion"):
            console.print(f"    -> {f['suggestion']}")

    if len(report["findings"]) > 30:
        console.print(f"\n  ... and {len(report['findings']) - 30} more")
    console.print()


# ---------------------------------------------------------------------------
# deploy — Generate deployment configs
# ---------------------------------------------------------------------------

@app.command()
def deploy(
    description: str = typer.Argument(..., help="Project description"),
    name: str = typer.Option("my-project", "--name", "-n", help="Project name"),
    output: str = typer.Option("./orchestrator-output", "--output", "-o", help="Output directory"),
    configs: str = typer.Option("all", "--configs", "-c", help="Configs: dockerfile,compose,ci,makefile,all"),
):
    """Generate deployment configurations."""
    from orchestrator_agent import state
    from orchestrator_agent.analyzers.project_planner import create_project_plan
    from orchestrator_agent.tools.generate_deployment import generate_deployment

    plan_data = create_project_plan(description, name)
    state.set_plan(plan_data)
    state.set_output_dir(output)

    result = generate_deployment(configs)
    text = result["content"][0]["text"]
    console.print(f"\n[bold cyan]Deployment Configs[/bold cyan]\n")
    console.print(text)
    console.print()


# ---------------------------------------------------------------------------
# ask — Free-form agent query
# ---------------------------------------------------------------------------

@app.command()
def ask(
    question: str = typer.Argument(..., help="Question for the orchestrator agent"),
):
    """Ask the orchestrator agent anything about software development."""
    from orchestrator_agent.agent import OrchestratorAgent
    agent = OrchestratorAgent()
    answer = agent.query(question)
    console.print()
    console.print(Markdown(answer))
    console.print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    app()


if __name__ == "__main__":
    main()
