"""refine_design MCP tool — improve existing UI code or spec."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

from ui_agent.state import store_generated


@tool(
    "refine_design",
    "Improve existing UI code. Provide either 'file_path' to read code from a file "
    "or 'code' as a string of existing code. Provide 'goals' describing the desired "
    "improvements (e.g., 'improve responsiveness, add hover states, better accessibility').",
    {"file_path": str, "code": str, "goals": str},
)
async def refine_design(args: dict[str, Any]) -> dict[str, Any]:
    file_path = args.get("file_path", "")
    code = args.get("code", "")
    goals = args.get("goals", "")

    if not goals:
        return {
            "content": [{"type": "text", "text": "Error: 'goals' is required."}],
            "is_error": True,
        }

    # Get the source code
    source_code = code
    source_name = "inline"

    if file_path:
        path = Path(file_path).resolve()
        if not path.exists():
            return {
                "content": [{"type": "text", "text": f"Error: File not found: {file_path}"}],
                "is_error": True,
            }
        source_code = path.read_text(errors="replace")
        source_name = path.name

    if not source_code:
        return {
            "content": [{"type": "text", "text": "Error: Provide 'file_path' or 'code'."}],
            "is_error": True,
        }

    result = {
        "source": source_name,
        "original_length": len(source_code),
        "goals": goals,
        "original_code": source_code,
        "refined_code": "",
        "changes_summary": "",
    }

    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(result, indent=2),
            }
        ],
    }
