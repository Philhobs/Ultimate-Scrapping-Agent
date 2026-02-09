"""rollback MCP tool — revert to a previous prompt version."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

from evolver_agent.state import (
    get_agent_profile, get_prompt_version, get_all_versions, add_improvement,
)


@tool(
    "rollback",
    "Revert to a previous prompt version. Restores from the version history. "
    "Provide 'version_id' to revert to (default: 0 = original baseline). "
    "Use 'list_versions' (bool) to see all available versions first.",
    {"version_id": int, "list_versions": bool},
)
async def rollback(args: dict[str, Any]) -> dict[str, Any]:
    list_versions_flag = args.get("list_versions", False)
    version_id = args.get("version_id", 0)

    versions = get_all_versions()

    if list_versions_flag or not versions:
        version_list = []
        for v in versions:
            version_list.append({
                "version_id": v.get("version_id", 0),
                "label": v.get("label", "unknown"),
                "strategy": v.get("source", "unknown"),
                "overall_score": v.get("scores", {}).get("overall", 0),
            })
        return {"content": [{"type": "text", "text": json.dumps({
            "versions": version_list,
            "total": len(version_list),
            "current": version_list[-1] if version_list else None,
        }, indent=2)}]}

    # Get the target version
    target = get_prompt_version(version_id)
    if target is None:
        return {
            "content": [{"type": "text", "text": f"Error: Version {version_id} not found."}],
            "is_error": True,
        }

    try:
        profile = get_agent_profile()
    except RuntimeError:
        return {
            "content": [{"type": "text", "text": "Error: Run analyze_agent first."}],
            "is_error": True,
        }

    prompt_file = profile.get("prompt_file")
    if not prompt_file:
        return {
            "content": [{"type": "text", "text": "Error: No prompt file path in agent profile."}],
            "is_error": True,
        }

    prompt_path = Path(prompt_file)
    if not prompt_path.exists():
        return {
            "content": [{"type": "text", "text": f"Error: Prompt file not found: {prompt_file}"}],
            "is_error": True,
        }

    # Write the rolled-back version
    rolled_back_prompt = target["prompt"]
    new_content = f'"""System prompt — rolled back by Evolver Agent."""\n\nSYSTEM_PROMPT = """\\\n{rolled_back_prompt}\n"""\n'
    prompt_path.write_text(new_content)

    # Log the rollback
    add_improvement({
        "version_id": version_id,
        "strategy": "rollback",
        "target_label": target.get("label", "unknown"),
        "prompt_file": str(prompt_path),
    })

    result = {
        "status": "rolled_back",
        "reverted_to_version": version_id,
        "label": target.get("label", "unknown"),
        "overall_score": target.get("scores", {}).get("overall", 0),
        "prompt_file": str(prompt_path),
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
