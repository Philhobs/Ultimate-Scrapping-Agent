"""security_scan MCP tool — scan for secrets, vulnerabilities, and policy violations."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from devops_agent.analyzers.security_scanner import scan_security
from devops_agent.state import set_security_findings, get_profile


@tool(
    "security_scan",
    "Scan the project for hardcoded secrets, vulnerable code patterns, sensitive "
    "files, and .gitignore gaps. Returns findings grouped by severity. "
    "Provide 'path' to the project root (uses analyzed project path by default).",
    {"path": str},
)
async def security_scan(args: dict[str, Any]) -> dict[str, Any]:
    path = args.get("path")
    if not path:
        try:
            profile = get_profile()
            path = profile.root
        except RuntimeError:
            return {
                "content": [{"type": "text", "text": "Error: Provide 'path' or run analyze_project first."}],
                "is_error": True,
            }

    findings = scan_security(path)
    set_security_findings(findings)

    # Group by severity
    by_severity: dict[str, list[dict]] = {"critical": [], "high": [], "medium": [], "low": []}
    for f in findings:
        by_severity.setdefault(f.severity, []).append(f.to_dict())

    result = {
        "total_findings": len(findings),
        "critical": len(by_severity.get("critical", [])),
        "high": len(by_severity.get("high", [])),
        "medium": len(by_severity.get("medium", [])),
        "low": len(by_severity.get("low", [])),
        "findings": by_severity,
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
