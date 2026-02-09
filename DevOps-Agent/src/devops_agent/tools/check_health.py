"""check_health MCP tool — analyze project deployment readiness."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from devops_agent.state import get_profile, get_security_findings


@tool(
    "check_health",
    "Analyze the project's deployment readiness. Returns a checklist of items: "
    "missing configs, security issues, testing gaps, and production requirements. "
    "Run analyze_project and security_scan first for best results.",
    {},
)
async def check_health(args: dict[str, Any]) -> dict[str, Any]:
    try:
        profile = get_profile()
    except RuntimeError:
        return {
            "content": [{"type": "text", "text": "Error: Run analyze_project first."}],
            "is_error": True,
        }

    checklist: list[dict[str, Any]] = []

    # Docker
    checklist.append({
        "category": "containerization",
        "item": "Dockerfile exists",
        "status": "pass" if profile.has_docker else "fail",
        "recommendation": None if profile.has_docker else "Generate a Dockerfile with generate_dockerfile.",
    })

    # CI/CD
    checklist.append({
        "category": "ci_cd",
        "item": "CI/CD pipeline configured",
        "status": "pass" if profile.has_ci else "fail",
        "recommendation": None if profile.has_ci else "Generate a pipeline with generate_ci_cd.",
    })

    # Tests
    checklist.append({
        "category": "testing",
        "item": "Test suite exists",
        "status": "pass" if profile.has_tests else "fail",
        "recommendation": None if profile.has_tests else "Add a tests/ directory with unit tests.",
    })

    # Git
    checklist.append({
        "category": "version_control",
        "item": "Git repository initialized",
        "status": "pass" if profile.has_git else "fail",
        "recommendation": None if profile.has_git else "Initialize git: git init",
    })

    # .env.example
    has_env_example = ".env.example" in profile.existing_files
    checklist.append({
        "category": "configuration",
        "item": ".env.example file exists",
        "status": "pass" if has_env_example else "warn",
        "recommendation": None if has_env_example else "Create .env.example documenting required env vars.",
    })

    # Entry point
    checklist.append({
        "category": "application",
        "item": "Entry point detected",
        "status": "pass" if profile.entry_point else "warn",
        "recommendation": None if profile.entry_point else "Ensure a clear entry point (main.py, index.js, etc.).",
    })

    # Health endpoint (suggest if web framework)
    if profile.framework in ("fastapi", "flask", "django", "express", "next.js", "nest.js", "gin", "echo"):
        checklist.append({
            "category": "monitoring",
            "item": "Health check endpoint (/health)",
            "status": "info",
            "recommendation": "Ensure your app has a /health endpoint for container probes.",
        })

    # Security findings
    findings = get_security_findings()
    critical = sum(1 for f in findings if f.severity == "critical")
    high = sum(1 for f in findings if f.severity == "high")

    checklist.append({
        "category": "security",
        "item": "No critical security findings",
        "status": "fail" if critical > 0 else "pass",
        "recommendation": f"Fix {critical} critical finding(s)." if critical else None,
    })

    checklist.append({
        "category": "security",
        "item": "No high-severity findings",
        "status": "warn" if high > 0 else "pass",
        "recommendation": f"Review {high} high-severity finding(s)." if high else None,
    })

    # Dependencies documented
    has_deps = bool(profile.dependencies)
    checklist.append({
        "category": "dependencies",
        "item": "Dependencies documented",
        "status": "pass" if has_deps else "warn",
        "recommendation": None if has_deps else "Add a requirements.txt or package.json.",
    })

    # Summary
    passed = sum(1 for c in checklist if c["status"] == "pass")
    failed = sum(1 for c in checklist if c["status"] == "fail")
    warnings = sum(1 for c in checklist if c["status"] == "warn")

    score = round(passed / len(checklist) * 100) if checklist else 0

    result = {
        "readiness_score": f"{score}%",
        "passed": passed,
        "failed": failed,
        "warnings": warnings,
        "total_checks": len(checklist),
        "checklist": checklist,
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
