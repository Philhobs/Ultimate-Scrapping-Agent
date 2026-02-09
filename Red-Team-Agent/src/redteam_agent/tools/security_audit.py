"""security_audit MCP tool — deep static analysis for OWASP Top 10 vulnerabilities."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from redteam_agent.analyzers.vulnerability_scanner import scan_vulnerabilities
from redteam_agent.state import get_target, set_findings


@tool(
    "security_audit",
    "Deep static analysis for OWASP Top 10 vulnerabilities: SQL injection, XSS, "
    "command injection, path traversal, SSRF, insecure deserialization, weak crypto, "
    "hardcoded secrets, and more. Provide 'path' or uses scanned target.",
    {"path": str},
)
async def security_audit(args: dict[str, Any]) -> dict[str, Any]:
    path = args.get("path")
    if not path:
        try:
            target = get_target()
            path = target["root"]
        except RuntimeError:
            return {
                "content": [{"type": "text", "text": "Error: Provide 'path' or run scan_target first."}],
                "is_error": True,
            }

    findings = scan_vulnerabilities(path)
    set_findings(findings)

    # Group by severity and category
    by_severity: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    by_category: dict[str, int] = {}
    for f in findings:
        by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
        by_category[f.category] = by_category.get(f.category, 0) + 1

    # Top findings details
    top_findings = [f.to_dict() for f in findings[:30]]

    result = {
        "total_findings": len(findings),
        "by_severity": by_severity,
        "by_category": by_category,
        "critical_count": by_severity["critical"],
        "high_count": by_severity["high"],
        "findings": top_findings,
        "owasp_categories": list(set(f.owasp for f in findings if f.owasp)),
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
