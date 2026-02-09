"""generate_report MCP tool — generate a DevOps readiness report."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

from devops_agent.state import (
    get_profile, get_security_findings, list_generated, get_output_dir,
)


@tool(
    "generate_report",
    "Generate a comprehensive DevOps readiness report in Markdown. "
    "Covers: project profile, security findings, CI/CD status, "
    "containerization, infrastructure, and recommendations. "
    "Optional 'title' and 'recommendations' (your analysis text).",
    {"title": str, "recommendations": str},
)
async def generate_report(args: dict[str, Any]) -> dict[str, Any]:
    try:
        profile = get_profile()
    except RuntimeError:
        return {
            "content": [{"type": "text", "text": "Error: Run analyze_project first."}],
            "is_error": True,
        }

    title = args.get("title", f"DevOps Report: {profile.name}")
    recommendations = args.get("recommendations", "")

    sections: list[str] = []

    # Header
    sections.append(f"# {title}\n")
    sections.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")

    # Project Overview
    sections.append("## Project Overview\n")
    sections.append(f"| Property | Value |")
    sections.append(f"|----------|-------|")
    sections.append(f"| Name | {profile.name} |")
    sections.append(f"| Language | {profile.language} |")
    sections.append(f"| Framework | {profile.framework or 'None detected'} |")
    sections.append(f"| Package Manager | {profile.package_manager or 'Unknown'} |")
    sections.append(f"| Entry Point | `{profile.entry_point or 'Not detected'}` |")
    sections.append(f"| Files | {profile.file_count} |")
    sections.append(f"| Lines of Code | {profile.total_lines:,} |")
    sections.append(f"| Dependencies | {len(profile.dependencies)} |")
    sections.append("")

    # Current State
    sections.append("## Current DevOps State\n")
    sections.append(f"| Component | Status |")
    sections.append(f"|-----------|--------|")
    sections.append(f"| Git | {'Yes' if profile.has_git else 'No'} |")
    sections.append(f"| Docker | {'Yes' if profile.has_docker else 'No'} |")
    sections.append(f"| CI/CD | {'Yes' if profile.has_ci else 'No'} |")
    sections.append(f"| Tests | {'Yes' if profile.has_tests else 'No'} |")
    sections.append("")

    if profile.env_vars:
        sections.append("### Environment Variables\n")
        for var in profile.env_vars:
            sections.append(f"- `{var}`")
        sections.append("")

    if profile.ports:
        sections.append(f"### Ports: {', '.join(str(p) for p in profile.ports)}\n")

    # Security
    findings = get_security_findings()
    if findings:
        sections.append("## Security Scan Results\n")
        by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for f in findings:
            by_severity[f.severity] = by_severity.get(f.severity, 0) + 1

        sections.append(f"| Severity | Count |")
        sections.append(f"|----------|-------|")
        for sev, count in by_severity.items():
            emoji = {"critical": "!!!", "high": "!!", "medium": "!", "low": "-"}
            if count > 0:
                sections.append(f"| {sev.upper()} {emoji.get(sev, '')} | {count} |")
        sections.append("")

        # List critical and high
        important = [f for f in findings if f.severity in ("critical", "high")]
        if important:
            sections.append("### Critical/High Findings\n")
            for f in important[:10]:
                sections.append(f"- **{f.category}** in `{f.file}:{f.line}` — {f.message}")
            sections.append("")
    else:
        sections.append("## Security: No scan performed yet\n")

    # Generated Files
    generated = list_generated()
    if generated:
        sections.append("## Generated Artifacts\n")
        for fname, size in generated.items():
            sections.append(f"- `{fname}` ({size:,} chars)")
        sections.append("")

    # Recommendations
    if recommendations:
        sections.append("## Recommendations\n")
        sections.append(recommendations)
        sections.append("")

    # Write report
    report_text = "\n".join(sections)
    out = Path(get_output_dir())
    out.mkdir(parents=True, exist_ok=True)
    report_path = str(out / "devops-report.md")
    Path(report_path).write_text(report_text)

    result = {
        "report_path": report_path,
        "length_chars": len(report_text),
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
