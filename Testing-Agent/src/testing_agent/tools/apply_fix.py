"""apply_fix MCP tool — apply code fixes to source files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

from testing_agent.state import get_profile, add_fix


@tool(
    "apply_fix",
    "Apply a code fix by replacing text in a source file. "
    "Provide 'file' (relative to project root), 'old_text' (exact text to replace), "
    "and 'new_text' (replacement text). "
    "Alternatively, provide 'file' and 'content' to overwrite the entire file.",
    {"file": str, "old_text": str, "new_text": str, "content": str},
)
async def apply_fix(args: dict[str, Any]) -> dict[str, Any]:
    try:
        profile = get_profile()
    except RuntimeError:
        return {
            "content": [{"type": "text", "text": "Error: Run analyze_codebase first."}],
            "is_error": True,
        }

    file_rel = args.get("file", "")
    old_text = args.get("old_text")
    new_text = args.get("new_text")
    full_content = args.get("content")

    if not file_rel:
        return {
            "content": [{"type": "text", "text": "Error: Provide 'file' parameter."}],
            "is_error": True,
        }

    file_path = Path(profile.root) / file_rel
    if not file_path.exists() and full_content is None:
        return {
            "content": [{"type": "text", "text": f"Error: File not found: {file_rel}"}],
            "is_error": True,
        }

    if full_content is not None:
        # Overwrite entire file
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(full_content)
        add_fix({
            "file": file_rel,
            "type": "overwrite",
            "lines_written": full_content.count("\n") + 1,
        })
        result = {
            "status": "applied",
            "file": file_rel,
            "type": "overwrite",
        }

    elif old_text and new_text is not None:
        # Text replacement
        try:
            content = file_path.read_text(errors="replace")
        except OSError as e:
            return {
                "content": [{"type": "text", "text": f"Error reading file: {e}"}],
                "is_error": True,
            }

        if old_text not in content:
            return {
                "content": [{"type": "text", "text": json.dumps({
                    "status": "error",
                    "message": "old_text not found in file. Check exact whitespace and content.",
                    "file": file_rel,
                }, indent=2)}],
                "is_error": True,
            }

        count = content.count(old_text)
        new_content = content.replace(old_text, new_text, 1)
        file_path.write_text(new_content)

        add_fix({
            "file": file_rel,
            "type": "replacement",
            "occurrences": count,
        })

        result = {
            "status": "applied",
            "file": file_rel,
            "type": "replacement",
            "occurrences_found": count,
            "replaced_first": True,
        }

    else:
        return {
            "content": [{"type": "text", "text": "Error: Provide either (old_text + new_text) or content."}],
            "is_error": True,
        }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
