"""MCP tool: review_code — AI-powered code review on generated files."""

from __future__ import annotations

from claude_agent_sdk import tool

from orchestrator_agent.analyzers.code_reviewer import review_project
from orchestrator_agent import state


@tool(
    "review_code",
    "Run a code review on all generated files. "
    "Checks for security vulnerabilities, code quality issues, "
    "best practices violations, naming, and complexity. "
    "Optional 'files' is a comma-separated list of relative paths to review.",
    {"files": str},
)
def review_code(files: str = "") -> dict:
    all_files = state.get_all_files()
    if not all_files:
        return {
            "content": [
                {"type": "text", "text": "No generated files to review. Write some files first."}
            ]
        }

    if files.strip():
        requested = [f.strip() for f in files.split(",")]
        to_review = {k: v for k, v in all_files.items() if k in requested}
    else:
        to_review = all_files

    report = review_project(to_review)
    state.set_review_findings(report["findings"])

    lines = [
        f"Code Review: {report['total_files_reviewed']} files reviewed",
        f"  Critical: {report['critical']}",
        f"  Warnings: {report['warnings']}",
        f"  Info: {report['info']}",
        f"  Passed: {'YES' if report['passed'] else 'NO — fix critical issues'}",
        "",
    ]
    for f in report["findings"][:20]:
        marker = {"critical": "!!!", "warning": "!!", "info": "i"}.get(f["severity"], "?")
        lines.append(f"  [{marker}] {f['file']}:{f['line']} — {f['message']}")
        if f.get("suggestion"):
            lines.append(f"        -> {f['suggestion']}")

    if len(report["findings"]) > 20:
        lines.append(f"  ... and {len(report['findings']) - 20} more findings")

    return {
        "content": [{"type": "text", "text": "\n".join(lines)}]
    }
