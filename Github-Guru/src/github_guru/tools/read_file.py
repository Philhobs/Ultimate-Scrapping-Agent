"""read_file MCP tool — read file contents from the repo."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

from github_guru.state import get_repo_root

MAX_CHARS = 30_000


@tool(
    "read_file",
    "Read the contents of a file. Supports optional line range. "
    "Returns content with line numbers. Truncates at 30K characters.",
    {"filepath": str, "start_line": int, "end_line": int},
)
async def read_file(args: dict[str, Any]) -> dict[str, Any]:
    repo_root = get_repo_root()
    filepath = args["filepath"]
    start_line = args.get("start_line")
    end_line = args.get("end_line")

    full_path = Path(repo_root) / filepath

    if not full_path.exists():
        return {
            "content": [{"type": "text", "text": f"File not found: {filepath}"}],
            "is_error": True,
        }

    try:
        content = full_path.read_text(errors="replace")
    except OSError as e:
        return {
            "content": [{"type": "text", "text": f"Error reading file: {e}"}],
            "is_error": True,
        }

    lines = content.split("\n")

    if start_line is not None or end_line is not None:
        s = (start_line or 1) - 1  # 1-indexed to 0-indexed
        e = end_line or len(lines)
        selected = lines[s:e]
        numbered = [f"{s + i + 1:4d} | {line}" for i, line in enumerate(selected)]
    else:
        numbered = [f"{i + 1:4d} | {line}" for i, line in enumerate(lines)]

    result = "\n".join(numbered)
    if len(result) > MAX_CHARS:
        result = result[:MAX_CHARS] + "\n... [truncated]"

    return {
        "content": [{
            "type": "text",
            "text": result,
        }]
    }
