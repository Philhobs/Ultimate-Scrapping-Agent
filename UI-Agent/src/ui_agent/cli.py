"""CLI interface for UI Agent using Typer + Rich."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

app = typer.Typer(
    name="ui-agent",
    help="AI-powered UI designer: generate frontend code from text descriptions and clone designs from screenshots.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def generate(
    description: str = typer.Argument(help="Description of the UI to generate"),
    name: str = typer.Option("app", "--name", "-n", help="App/project name"),
    framework: str = typer.Option("html", "--framework", "-f", help="Output framework: html or react"),
    output: str = typer.Option("./ui-output", "--output", "-o", help="Output directory"),
    path: str = typer.Option(".", "--path", "-p", help="Existing project directory to scan"),
) -> None:
    """Generate a full UI from a text description."""
    from ui_agent.agent import UIAgent
    from ui_agent import state

    state.set_output_dir(str(Path(output).resolve()))

    agent = UIAgent()

    resolved = str(Path(path).resolve())
    if Path(resolved).is_dir():
        agent.analyze(resolved)

    console.print(f"\n[bold cyan]Generating UI: {name}[/]\n")

    query = (
        f"Generate a complete UI for '{name}' using the {framework} framework.\n\n"
        f"Description: {description}\n\n"
        "Steps:\n"
        "1. Generate a UI spec with layout, components, and design tokens\n"
        "2. Generate each component\n"
        "3. Generate the full page assembling all components\n"
        "4. Generate a style guide\n"
        "5. Export all files to disk\n\n"
        "Make the design modern, responsive, and accessible."
    )

    answer = asyncio.run(agent.run(query))
    console.print(Markdown(answer))

    _show_generated_files()


@app.command()
def clone(
    image: str = typer.Argument(help="Path to screenshot/image to clone"),
    name: str = typer.Option("cloned-ui", "--name", "-n", help="Name for the cloned UI"),
    framework: str = typer.Option("html", "--framework", "-f", help="Output framework: html or react"),
    output: str = typer.Option("./ui-output", "--output", "-o", help="Output directory"),
) -> None:
    """Clone a design from a screenshot/image file."""
    from ui_agent.agent import UIAgent
    from ui_agent import state

    image_path = Path(image).resolve()
    if not image_path.exists():
        console.print(f"[red]Image not found: {image}[/]")
        raise typer.Exit(1)

    state.set_output_dir(str(Path(output).resolve()))
    state.set_image_path(str(image_path))

    agent = UIAgent()

    console.print(f"\n[bold cyan]Cloning design from: {image_path.name}[/]\n")

    query = (
        f"Clone the design from the provided screenshot into {framework} code.\n\n"
        "Steps:\n"
        f"1. Use read_image to load the screenshot at: {image_path}\n"
        "2. Analyze the image: extract layout structure, color palette, typography, "
        "spacing, component hierarchy, and visual patterns\n"
        "3. Generate a UI spec matching the analyzed design\n"
        "4. Generate each identified component\n"
        "5. Generate the full page to match the screenshot as closely as possible\n"
        "6. Export all files to disk\n\n"
        f"Project name: {name}\n"
        "Make the output responsive and pixel-accurate to the original design."
    )

    answer = asyncio.run(agent.run(query))
    console.print(Markdown(answer))

    _show_generated_files()


@app.command()
def component(
    description: str = typer.Argument(help="Component name and/or description"),
    framework: str = typer.Option("html", "--framework", "-f", help="Output framework: html or react"),
    output: str = typer.Option("./ui-output", "--output", "-o", help="Output directory"),
) -> None:
    """Generate a single reusable UI component."""
    from ui_agent.agent import UIAgent
    from ui_agent import state

    state.set_output_dir(str(Path(output).resolve()))

    agent = UIAgent()

    console.print(f"\n[bold cyan]Generating component: {description}[/]\n")

    query = (
        f"Generate a reusable {framework} component based on this description: {description}\n\n"
        "Steps:\n"
        "1. Generate the component with proper states (default, hover, focus, disabled)\n"
        "2. Export the component file to disk\n\n"
        "Make it responsive, accessible, and production-ready with Tailwind CSS."
    )

    answer = asyncio.run(agent.run(query))
    console.print(Markdown(answer))

    _show_generated_files()


@app.command()
def refine(
    path: str = typer.Argument(help="Path to UI file to refine"),
    goals: str = typer.Option("improve responsiveness and accessibility", "--goals", "-g", help="Improvement goals"),
    output: str = typer.Option("./ui-output", "--output", "-o", help="Output directory"),
) -> None:
    """Refine existing UI code with improvements."""
    from ui_agent.agent import UIAgent
    from ui_agent import state

    resolved = Path(path).resolve()
    if not resolved.exists():
        console.print(f"[red]File not found: {path}[/]")
        raise typer.Exit(1)

    state.set_output_dir(str(Path(output).resolve()))

    agent = UIAgent()

    console.print(f"\n[bold cyan]Refining: {resolved.name}[/]\n")
    console.print(f"[blue]Goals:[/] {goals}\n")

    query = (
        f"Refine the UI code in the file at: {resolved}\n\n"
        f"Improvement goals: {goals}\n\n"
        "Steps:\n"
        f"1. Read the existing file at {resolved}\n"
        "2. Analyze the current code and identify areas for improvement\n"
        "3. Apply the refinements based on the goals\n"
        "4. Export the refined code to disk\n\n"
        "Preserve the existing design intent while applying improvements."
    )

    answer = asyncio.run(agent.run(query))
    console.print(Markdown(answer))

    _show_generated_files()


@app.command()
def ask(
    question: str = typer.Argument(help="UI/design question"),
    path: str = typer.Option(".", "--path", "-p", help="Project directory for context"),
) -> None:
    """Ask any UI/design question."""
    from ui_agent.agent import UIAgent

    agent = UIAgent()

    console.print(f"\n[bold blue]Question:[/] {question}\n")

    answer = asyncio.run(agent.run(question, project_path=path))
    console.print(Markdown(answer))


def _show_generated_files() -> None:
    """Display a table of generated files."""
    from ui_agent import state

    generated = state.list_generated()
    if not generated:
        return

    table = Table(title="Generated Files", title_style="bold green")
    table.add_column("File", style="cyan")
    table.add_column("Size", style="white", justify="right")

    for filename, size in generated.items():
        table.add_row(filename, f"{size:,} chars")

    console.print()
    console.print(table)
    console.print(f"\n[green]Output directory:[/] {state.get_output_dir()}")


def main() -> None:
    app()
