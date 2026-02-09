"""analyze_project MCP tool — scan a project to build a deployment profile."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from devops_agent.analyzers.project_scanner import scan_project
from devops_agent.state import set_profile


@tool(
    "analyze_project",
    "Scan a project directory to detect language, framework, dependencies, "
    "entry point, existing Docker/CI configs, env vars, and ports. "
    "Provide 'path' to the project root.",
    {"path": str},
)
async def analyze_project(args: dict[str, Any]) -> dict[str, Any]:
    path = args.get("path", ".")

    try:
        profile = scan_project(path)
    except FileNotFoundError as e:
        return {
            "content": [{"type": "text", "text": f"Error: {e}"}],
            "is_error": True,
        }

    set_profile(profile)

    result = profile.to_dict()
    result["dependencies"] = profile.dependencies[:30]
    result["existing_files"] = profile.existing_files
    result["scripts"] = profile.scripts

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
