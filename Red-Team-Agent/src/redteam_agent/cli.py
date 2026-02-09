"""CLI interface for Red-Team Agent using Typer + Rich."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

app = typer.Typer(
    name="redteam-agent",
    help="AI-powered adversarial red-team agent: ethical security testing, prompt injection detection, vulnerability assessment.",
    no_args_is_help=True,
)
console = Console()


@app.command()
def assess(
    path: str = typer.Argument(".", help="Target project directory"),
    output: str = typer.Option("./redteam-output", "--output", "-o", help="Output directory for report"),
) -> None:
    """Full red-team assessment: scan, audit, test auth, check defenses, and report."""
    from redteam_agent.agent import RedTeamAgent
    from redteam_agent import state

    resolved = str(Path(path).resolve())
    if not Path(resolved).is_dir():
        console.print(f"[red]Not a directory: {path}[/]")
        raise typer.Exit(1)

    state.set_output_dir(str(Path(output).resolve()))
    agent = RedTeamAgent()
    agent.scan(resolved)

    console.print(f"\n[bold red]Running full red-team assessment...[/]\n")

    query = (
        f"I've already pre-scanned the target at {resolved}. Now do a full red-team assessment:\n"
        "1. scan_target to map the attack surface\n"
        "2. security_audit for OWASP Top 10 vulnerabilities\n"
        "3. test_auth to probe authentication weaknesses\n"
        "4. generate_payloads for discovered attack vectors\n"
        "5. check_defenses to evaluate security controls\n"
        "6. generate_report with executive summary and remediation roadmap\n\n"
        "Be thorough. Explain each finding and its real-world impact."
    )

    answer = asyncio.run(agent.run(query))
    console.print(Markdown(answer))


@app.command()
def scan(
    path: str = typer.Argument(".", help="Target project directory"),
) -> None:
    """Reconnaissance: scan the attack surface of a project."""
    from redteam_agent.agent import RedTeamAgent

    resolved = str(Path(path).resolve())
    if not Path(resolved).is_dir():
        console.print(f"[red]Not a directory: {path}[/]")
        raise typer.Exit(1)

    agent = RedTeamAgent()

    console.print(f"\n[bold red]Scanning attack surface...[/]\n")

    query = (
        f"Scan the target at {resolved} using scan_target. "
        "Present a detailed attack surface map: endpoints, input handlers, "
        "auth mechanisms, external calls, and sensitive files."
    )

    answer = asyncio.run(agent.run(query, target_path=resolved))
    console.print(Markdown(answer))


@app.command()
def audit(
    path: str = typer.Argument(".", help="Target project directory"),
) -> None:
    """Deep security audit for OWASP Top 10 vulnerabilities."""
    from redteam_agent.agent import RedTeamAgent

    resolved = str(Path(path).resolve())
    agent = RedTeamAgent()
    agent.scan(resolved)

    console.print(f"\n[bold red]Running security audit...[/]\n")

    query = (
        f"Run a security_audit on {resolved}. "
        "Present all findings grouped by OWASP category, with severity, "
        "affected code, and specific remediation steps."
    )

    answer = asyncio.run(agent.run(query))
    console.print(Markdown(answer))


@app.command()
def prompt_test(
    attack_type: str = typer.Option(None, "--type", "-t", help="Attack type: override, extraction, escape, encoding"),
) -> None:
    """Generate prompt injection test cases for LLM/AI systems."""
    from redteam_agent.agent import RedTeamAgent

    agent = RedTeamAgent()

    console.print(f"\n[bold red]Generating prompt injection tests...[/]\n")

    type_str = f" Focus on attack type: {attack_type}." if attack_type else ""
    query = (
        f"Generate prompt injection test cases.{type_str} "
        "For each test case, explain the attack vector, expected safe behavior, "
        "and detection patterns. Include remediation advice."
    )

    answer = asyncio.run(agent.run(query))
    console.print(Markdown(answer))


@app.command()
def payloads(
    category: str = typer.Argument("all", help="Category: sqli, xss, cmdi, path_traversal, ssrf, auth, prompt_injection, fuzz, all"),
) -> None:
    """Generate security test payloads for a specific attack category."""
    from redteam_agent.agent import RedTeamAgent

    agent = RedTeamAgent()

    console.print(f"\n[bold red]Generating {category} payloads...[/]\n")

    query = (
        f"Generate test payloads for category: {category}. "
        "Explain each payload, when to use it, and what a vulnerable vs. secure response looks like."
    )

    answer = asyncio.run(agent.run(query))
    console.print(Markdown(answer))


@app.command()
def defenses(
    path: str = typer.Argument(".", help="Target project directory"),
) -> None:
    """Evaluate existing security defenses and score them."""
    from redteam_agent.agent import RedTeamAgent

    resolved = str(Path(path).resolve())
    agent = RedTeamAgent()

    console.print(f"\n[bold red]Evaluating security defenses...[/]\n")

    query = (
        f"Scan the target at {resolved} and then check_defenses. "
        "Score each defense area, highlight weaknesses, and provide "
        "prioritized improvement recommendations."
    )

    answer = asyncio.run(agent.run(query, target_path=resolved))
    console.print(Markdown(answer))


@app.command()
def ask(
    question: str = typer.Argument(help="Security question about your project"),
    path: str = typer.Option(".", "--path", "-p", help="Target project directory"),
    output: str = typer.Option("./redteam-output", "--output", "-o", help="Output directory"),
) -> None:
    """Ask any security question about your project."""
    from redteam_agent.agent import RedTeamAgent
    from redteam_agent import state

    resolved = str(Path(path).resolve())
    state.set_output_dir(str(Path(output).resolve()))
    agent = RedTeamAgent()

    console.print(f"\n[bold red]Question:[/] {question}\n")

    answer = asyncio.run(agent.run(question, target_path=resolved))
    console.print(Markdown(answer))


def main() -> None:
    app()
