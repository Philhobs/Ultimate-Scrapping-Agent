"""CLI interface for Testing Agent using Typer + Rich."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

app = typer.Typer(
    name="testing-agent",
    help="AI-powered QA engineer: test generation, debugging, coverage analysis, and performance profiling.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def qa(
    path: str = typer.Argument(".", help="Project directory to test"),
    output: str = typer.Option("./testing-output", "--output", "-o", help="Output directory for generated tests"),
) -> None:
    """Full QA cycle: analyze, check coverage, generate tests, run, debug, and fix."""
    from testing_agent.agent import TestingAgent
    from testing_agent import state

    resolved = str(Path(path).resolve())
    if not Path(resolved).is_dir():
        console.print(f"[red]Not a directory: {path}[/]")
        raise typer.Exit(1)

    state.set_output_dir(str(Path(output).resolve()))
    agent = TestingAgent()
    agent.analyze(resolved)

    console.print(f"\n[bold cyan]Running full QA cycle...[/]\n")

    query = (
        f"I've already analyzed the codebase at {resolved}. Now do a full QA cycle:\n"
        "1. Check test coverage to find untested functions\n"
        "2. Generate tests for the most critical uncovered functions\n"
        "3. Run the full test suite\n"
        "4. If any tests fail, debug the failures and identify root causes\n"
        "5. Suggest fixes for any bugs found\n"
        "6. Profile performance if tests pass\n\n"
        "Report your findings and recommendations."
    )

    answer = asyncio.run(agent.run(query))
    console.print(Markdown(answer))


@app.command()
def scan(
    path: str = typer.Argument(".", help="Project directory to scan"),
) -> None:
    """Analyze a project's codebase structure, functions, and existing tests."""
    from testing_agent.agent import TestingAgent

    resolved = str(Path(path).resolve())
    if not Path(resolved).is_dir():
        console.print(f"[red]Not a directory: {path}[/]")
        raise typer.Exit(1)

    agent = TestingAgent()
    info = agent.analyze(resolved)

    table = Table(title="Codebase Profile", title_style="bold cyan")
    table.add_column("Property", style="green")
    table.add_column("Value", style="white")
    for key, val in info.items():
        table.add_row(key.replace("_", " ").title(), str(val))
    console.print(table)


@app.command()
def test(
    path: str = typer.Argument(".", help="Project directory"),
    target: str = typer.Option(None, "--target", "-t", help="Specific test file or test name"),
) -> None:
    """Run the test suite and show results."""
    from testing_agent.agent import TestingAgent

    resolved = str(Path(path).resolve())
    agent = TestingAgent()
    agent.analyze(resolved)

    console.print(f"\n[bold cyan]Running tests...[/]\n")

    target_msg = f" (target: {target})" if target else ""
    query = (
        f"Run the test suite{target_msg} and present the results. "
        "Show which tests passed, failed, and any error messages. "
        "If there are failures, use debug_failure to analyze them."
    )
    if target:
        query = f"Run tests with target='{target}'. " + query

    answer = asyncio.run(agent.run(query))
    console.print(Markdown(answer))


@app.command()
def coverage(
    path: str = typer.Argument(".", help="Project directory"),
) -> None:
    """Analyze test coverage and show untested functions."""
    from testing_agent.agent import TestingAgent

    resolved = str(Path(path).resolve())
    agent = TestingAgent()
    agent.analyze(resolved)

    console.print(f"\n[bold cyan]Analyzing test coverage...[/]\n")

    query = (
        "Check test coverage for this project. "
        "Show which functions are covered, which aren't, and the overall coverage percentage. "
        "Prioritize the most critical untested functions."
    )

    answer = asyncio.run(agent.run(query))
    console.print(Markdown(answer))


@app.command()
def generate(
    path: str = typer.Argument(".", help="Project directory"),
    file: str = typer.Option(None, "--file", "-f", help="Specific source file to generate tests for"),
    output: str = typer.Option("./testing-output", "--output", "-o", help="Output directory"),
) -> None:
    """Generate tests for untested functions."""
    from testing_agent.agent import TestingAgent
    from testing_agent import state

    resolved = str(Path(path).resolve())
    state.set_output_dir(str(Path(output).resolve()))
    agent = TestingAgent()
    agent.analyze(resolved)

    console.print(f"\n[bold cyan]Generating tests...[/]\n")

    if file:
        query = (
            f"Generate comprehensive tests for the file: {file}\n"
            "Read the source code first, then generate tests covering:\n"
            "- Happy path for each function\n"
            "- Edge cases (empty, null, boundary values)\n"
            "- Error handling paths\n"
        )
    else:
        query = (
            "Check coverage and generate tests for the most critical untested functions. "
            "Read the source code first, then generate thorough tests."
        )

    answer = asyncio.run(agent.run(query))
    console.print(Markdown(answer))


@app.command()
def debug(
    path: str = typer.Argument(".", help="Project directory"),
    error: str = typer.Option(None, "--error", "-e", help="Error message or test name to debug"),
) -> None:
    """Debug test failures or errors."""
    from testing_agent.agent import TestingAgent

    resolved = str(Path(path).resolve())
    agent = TestingAgent()
    agent.analyze(resolved)

    console.print(f"\n[bold cyan]Debugging...[/]\n")

    if error:
        query = (
            f"Debug this error/failure: {error}\n\n"
            "1. Run the tests to reproduce the failure\n"
            "2. Analyze the stack trace and error\n"
            "3. Read the relevant source code\n"
            "4. Identify the root cause\n"
            "5. Suggest a specific fix with code"
        )
    else:
        query = (
            "Run the test suite, and for any failures:\n"
            "1. Analyze each failure using debug_failure\n"
            "2. Read the relevant source code\n"
            "3. Identify root causes\n"
            "4. Suggest specific fixes with code diffs"
        )

    answer = asyncio.run(agent.run(query))
    console.print(Markdown(answer))


@app.command()
def ask(
    question: str = typer.Argument(help="Testing/debugging question about your project"),
    path: str = typer.Option(".", "--path", "-p", help="Project directory"),
    output: str = typer.Option("./testing-output", "--output", "-o", help="Output directory"),
) -> None:
    """Ask any testing or debugging question about your project."""
    from testing_agent.agent import TestingAgent
    from testing_agent import state

    resolved = str(Path(path).resolve())
    state.set_output_dir(str(Path(output).resolve()))
    agent = TestingAgent()

    console.print(f"\n[bold blue]Question:[/] {question}\n")

    answer = asyncio.run(agent.run(question, project_path=resolved))
    console.print(Markdown(answer))


def main() -> None:
    app()
