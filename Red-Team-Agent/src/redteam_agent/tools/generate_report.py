"""generate_report MCP tool — generate a comprehensive red-team assessment report."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

from redteam_agent.state import (
    get_target, get_findings, get_payload_results,
    get_defense_evals, get_output_dir,
)


@tool(
    "generate_report",
    "Generate a comprehensive red-team assessment report in Markdown. Covers: "
    "executive summary, methodology, findings by severity, attack narratives, "
    "remediation roadmap, and risk matrix. "
    "Optional: 'title', 'executive_summary', 'recommendations' (your analysis).",
    {"title": str, "executive_summary": str, "recommendations": str},
)
async def generate_report(args: dict[str, Any]) -> dict[str, Any]:
    try:
        target = get_target()
    except RuntimeError:
        return {
            "content": [{"type": "text", "text": "Error: Run scan_target first."}],
            "is_error": True,
        }

    title = args.get("title", f"Red-Team Assessment: {target['name']}")
    executive_summary = args.get("executive_summary", "")
    recommendations = args.get("recommendations", "")

    sections: list[str] = []

    # Header
    sections.append(f"# {title}\n")
    sections.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    sections.append(f"*Target: {target['name']}*")
    sections.append(f"*Scope: Source code analysis, vulnerability assessment, defense evaluation*\n")

    # Classification banner
    sections.append("> **CONFIDENTIAL** — This report contains security-sensitive findings.")
    sections.append("> Handle according to your organization's security policy.\n")

    # Executive Summary
    if executive_summary:
        sections.append("## Executive Summary\n")
        sections.append(executive_summary)
        sections.append("")

    # Target Profile
    sections.append("## Target Profile\n")
    sections.append("| Property | Value |")
    sections.append("|----------|-------|")
    sections.append(f"| Name | {target['name']} |")
    sections.append(f"| Language | {target['language']} |")
    sections.append(f"| Framework | {target.get('framework') or 'None detected'} |")
    sections.append(f"| Files Scanned | {target['total_files']} |")
    sections.append(f"| Lines of Code | {target['total_lines']:,} |")
    sections.append(f"| Endpoints | {target.get('endpoints_found', len(target.get('endpoints', [])))} |")
    sections.append(f"| Tech Stack | {', '.join(target.get('tech_stack', []))} |")
    sections.append("")

    # Vulnerability Findings
    findings = get_findings()
    if findings:
        sections.append("## Vulnerability Findings\n")

        by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for f in findings:
            by_severity[f.severity] = by_severity.get(f.severity, 0) + 1

        # Risk matrix
        sections.append("### Risk Summary\n")
        sections.append("| Severity | Count | Action |")
        sections.append("|----------|-------|--------|")
        actions = {
            "critical": "Immediate fix required",
            "high": "Fix within 1 sprint",
            "medium": "Fix within 1 month",
            "low": "Fix when convenient",
            "info": "Consider implementing",
        }
        for sev in ("critical", "high", "medium", "low", "info"):
            if by_severity[sev] > 0:
                icon = {"critical": "!!!", "high": "!!", "medium": "!", "low": "-", "info": "i"}
                sections.append(f"| {sev.upper()} {icon[sev]} | {by_severity[sev]} | {actions[sev]} |")
        sections.append("")

        # Detailed findings (critical + high)
        important = [f for f in findings if f.severity in ("critical", "high")]
        if important:
            sections.append("### Critical & High Severity Findings\n")
            for i, f in enumerate(important[:20], 1):
                sections.append(f"#### {i}. [{f.severity.upper()}] {f.category}\n")
                sections.append(f"- **File:** `{f.file}:{f.line}`")
                sections.append(f"- **Code:** `{f.code.strip()[:100]}`")
                sections.append(f"- **Issue:** {f.description}")
                if f.cwe:
                    sections.append(f"- **CWE:** {f.cwe}")
                if f.owasp:
                    sections.append(f"- **OWASP:** {f.owasp}")
                sections.append(f"- **Remediation:** {f.remediation}")
                sections.append("")

        # Medium/Low summary
        medium_low = [f for f in findings if f.severity in ("medium", "low")]
        if medium_low:
            sections.append("### Medium & Low Severity Findings\n")
            by_cat: dict[str, int] = {}
            for f in medium_low:
                by_cat[f.category] = by_cat.get(f.category, 0) + 1
            for cat, count in sorted(by_cat.items(), key=lambda x: -x[1]):
                sections.append(f"- **{cat}**: {count} finding(s)")
            sections.append("")
    else:
        sections.append("## Vulnerability Findings\n")
        sections.append("No vulnerability scan performed or no findings detected.\n")

    # Defense Evaluation
    evals = get_defense_evals()
    if evals:
        sections.append("## Defense Evaluation\n")
        sections.append("| Defense Area | Score | Status |")
        sections.append("|-------------|-------|--------|")
        for ev in sorted(evals, key=lambda x: x["score"]):
            status = "Pass" if ev["score"] >= 60 else "Needs Work" if ev["score"] >= 30 else "Fail"
            sections.append(f"| {ev['area']} | {ev['score']}/100 | {status} |")
        sections.append("")

        # Weak areas
        weak = [ev for ev in evals if ev["score"] < 60]
        if weak:
            sections.append("### Priority Improvements\n")
            for ev in sorted(weak, key=lambda x: x["score"]):
                sections.append(f"- **{ev['area']}** ({ev['score']}/100): {ev['recommendation']}")
            sections.append("")

    # Testing Summary
    payload_results = get_payload_results()
    if payload_results:
        sections.append("## Testing Summary\n")
        sections.append("| Test Type | Payloads Generated |")
        sections.append("|-----------|-------------------|")
        for pr in payload_results:
            sections.append(f"| {pr['tool']} | {pr.get('payloads_generated', pr.get('findings', 'N/A'))} |")
        sections.append("")

    # Recommendations
    if recommendations:
        sections.append("## Recommendations\n")
        sections.append(recommendations)
        sections.append("")

    # Remediation Roadmap
    if findings:
        sections.append("## Remediation Roadmap\n")
        critical_count = sum(1 for f in findings if f.severity == "critical")
        high_count = sum(1 for f in findings if f.severity == "high")
        medium_count = sum(1 for f in findings if f.severity == "medium")

        sections.append("### Phase 1 — Immediate (This Week)")
        sections.append(f"- Fix {critical_count} critical vulnerabilities")
        sections.append("- Rotate any exposed secrets/credentials")
        sections.append("- Enable security headers\n")

        sections.append("### Phase 2 — Short-term (This Sprint)")
        sections.append(f"- Address {high_count} high-severity findings")
        sections.append("- Implement input validation framework")
        sections.append("- Add rate limiting to auth endpoints\n")

        sections.append("### Phase 3 — Medium-term (This Quarter)")
        sections.append(f"- Fix {medium_count} medium-severity findings")
        sections.append("- Set up automated dependency scanning")
        sections.append("- Implement structured security logging")
        sections.append("- Schedule regular security reviews\n")

    # Footer
    sections.append("---")
    sections.append("*This report was generated by Red-Team Agent for authorized security testing purposes only.*")

    # Write report
    report_text = "\n".join(sections)
    out = Path(get_output_dir())
    out.mkdir(parents=True, exist_ok=True)
    report_path = str(out / "redteam-report.md")
    Path(report_path).write_text(report_text)

    result = {
        "report_path": report_path,
        "length_chars": len(report_text),
        "findings_included": len(findings),
        "defense_areas_evaluated": len(evals),
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
