"""read_file MCP tool — read existing code or design files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool


@tool(
    "read_file",
    "Read an existing code or design file and return its content. "
    "Provide 'path' to the file. Returns the file content as text.",
    {"path": str},
)
async def read_file(args: dict[str, Any]) -> dict[str, Any]:
    file_path = args.get("path", "")

    if not file_path:
        return {
            "content": [{"type": "text", "text": "Error: 'path' is required."}],
            "is_error": True,
        }

    path = Path(file_path).resolve()

    if not path.exists():
        return {
            "content": [{"type": "text", "text": f"Error: File not found: {file_path}"}],
            "is_error": True,
        }

    if not path.is_file():
        return {
            "content": [{"type": "text", "text": f"Error: Not a file: {file_path}"}],
            "is_error": True,
        }

    try:
        content = path.read_text(errors="replace")
    except OSError as e:
        return {
            "content": [{"type": "text", "text": f"Error reading file: {e}"}],
            "is_error": True,
        }

    # Truncate very large files
    max_chars = 100_000
    truncated = len(content) > max_chars
    if truncated:
        content = content[:max_chars]

    metadata = {
        "path": str(path),
        "name": path.name,
        "extension": path.suffix,
        "size_chars": len(content),
        "truncated": truncated,
    }

    return {
        "content": [
            {
                "type": "text",
                "text": f"File: {path.name} ({len(content):,} chars)\n"
                        f"---\n{content}",
            }
        ],
    }
