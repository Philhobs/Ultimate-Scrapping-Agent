"""read_source MCP tool — read a source file for inspection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

from testing_agent.state import get_profile


@tool(
    "read_source",
    "Read a source file (or specific line range) to inspect code. "
    "Provide 'file' (relative to project root). "
    "Optional: 'start_line' and 'end_line' for a specific range.",
    {"file": str, "start_line": int, "end_line": int},
)
async def read_source(args: dict[str, Any]) -> dict[str, Any]:
    file_rel = args.get("file", "")
    start_line = args.get("start_line")
    end_line = args.get("end_line")

    if not file_rel:
        return {
            "content": [{"type": "text", "text": "Error: Provide 'file' parameter."}],
            "is_error": True,
        }

    # Resolve path
    try:
        profile = get_profile()
        file_path = Path(profile.root) / file_rel
    except RuntimeError:
        file_path = Path(file_rel)

    if not file_path.exists():
        return {
            "content": [{"type": "text", "text": f"Error: File not found: {file_rel}"}],
            "is_error": True,
        }

    try:
        content = file_path.read_text(errors="replace")
    except OSError as e:
        return {
            "content": [{"type": "text", "text": f"Error reading file: {e}"}],
            "is_error": True,
        }

    lines = content.split("\n")
    total_lines = len(lines)

    # Apply line range if specified
    if start_line is not None or end_line is not None:
        s = max(0, (start_line or 1) - 1)
        e = min(total_lines, end_line or total_lines)
        selected = lines[s:e]
        # Add line numbers
        numbered = [f"{i + s + 1:4d} | {line}" for i, line in enumerate(selected)]
        display = "\n".join(numbered)
        line_info = f"Lines {s + 1}-{e} of {total_lines}"
    else:
        # Limit to 500 lines to avoid overwhelming context
        if total_lines > 500:
            numbered = [f"{i + 1:4d} | {line}" for i, line in enumerate(lines[:500])]
            display = "\n".join(numbered) + f"\n... (truncated, {total_lines - 500} more lines)"
        else:
            numbered = [f"{i + 1:4d} | {line}" for i, line in enumerate(lines)]
            display = "\n".join(numbered)
        line_info = f"{total_lines} lines"

    result = {
        "file": file_rel,
        "line_info": line_info,
        "content": display,
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
