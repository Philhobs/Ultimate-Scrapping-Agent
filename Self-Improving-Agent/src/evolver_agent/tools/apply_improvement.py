"""apply_improvement MCP tool — write an improved prompt back to the agent's files."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

from evolver_agent.state import (
    get_agent_profile, get_prompt_version, add_improvement, get_output_dir,
)


@tool(
    "apply_improvement",
    "Write an improved prompt version back to the agent's system_prompt.py file. "
    "Creates a timestamped backup first. Provide 'version_id' of the improved version "
    "to apply. Safety-degraded versions are rejected.",
    {"version_id": int, "force": bool},
)
async def apply_improvement(args: dict[str, Any]) -> dict[str, Any]:
    version_id = args.get("version_id")
    force = args.get("force", False)

    if version_id is None:
        return {
            "content": [{"type": "text", "text": "Error: Provide 'version_id' of the version to apply."}],
            "is_error": True,
        }

    try:
        profile = get_agent_profile()
    except RuntimeError:
        return {
            "content": [{"type": "text", "text": "Error: Run analyze_agent first."}],
            "is_error": True,
        }

    version = get_prompt_version(version_id)
    if version is None:
        return {
            "content": [{"type": "text", "text": f"Error: Version {version_id} not found."}],
            "is_error": True,
        }

    # Safety check — never apply if safety score is lower than baseline
    baseline = get_prompt_version(0)
    if baseline and not force:
        baseline_safety = baseline.get("scores", {}).get("safety", 0)
        new_safety = version.get("scores", {}).get("safety", 0)
        if new_safety < baseline_safety:
            return {"content": [{"type": "text", "text": json.dumps({
                "status": "rejected",
                "reason": "Safety score degraded",
                "baseline_safety": baseline_safety,
                "new_safety": new_safety,
                "hint": "Use force=true to override (not recommended).",
            }, indent=2)}]}

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

    # Create backup
    backup_dir = Path(get_output_dir()) / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"system_prompt_{timestamp}.py.bak"
    shutil.copy2(prompt_path, backup_path)

    # Write the improved prompt
    new_prompt = version["prompt"]
    new_content = f'"""System prompt — evolved by Evolver Agent."""\n\nSYSTEM_PROMPT = """\\\n{new_prompt}\n"""\n'

    prompt_path.write_text(new_content)

    # Log improvement
    improvement = {
        "version_id": version_id,
        "strategy": version.get("strategy", "unknown"),
        "timestamp": timestamp,
        "backup": str(backup_path),
        "old_scores": baseline.get("scores") if baseline else None,
        "new_scores": version.get("scores"),
        "prompt_file": str(prompt_path),
    }
    add_improvement(improvement)

    result = {
        "status": "applied",
        "version_id": version_id,
        "strategy": version.get("strategy", "unknown"),
        "prompt_file": str(prompt_path),
        "backup_file": str(backup_path),
        "old_overall": baseline.get("scores", {}).get("overall") if baseline else None,
        "new_overall": version.get("scores", {}).get("overall"),
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
