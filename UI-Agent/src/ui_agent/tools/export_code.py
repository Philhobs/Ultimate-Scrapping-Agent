"""export_code MCP tool — write generated code to files on disk."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

from ui_agent.state import store_generated, get_output_dir


@tool(
    "export_code",
    "Write generated code to a file on disk. Provide 'filename' and 'content'. "
    "Files are saved to the configured output directory. "
    "Optional 'subdirectory' to organize files (e.g., 'components', 'pages').",
    {"filename": str, "content": str, "subdirectory": str},
)
async def export_code(args: dict[str, Any]) -> dict[str, Any]:
    filename = args.get("filename", "")
    content = args.get("content", "")
    subdirectory = args.get("subdirectory", "")

    if not filename:
        return {
            "content": [{"type": "text", "text": "Error: 'filename' is required."}],
            "is_error": True,
        }

    if not content:
        return {
            "content": [{"type": "text", "text": "Error: 'content' is required."}],
            "is_error": True,
        }

    out = Path(get_output_dir())
    if subdirectory:
        out = out / subdirectory
    out.mkdir(parents=True, exist_ok=True)

    file_path = out / filename
    file_path.write_text(content)

    # Store in state with relative path
    store_key = f"{subdirectory}/{filename}" if subdirectory else filename
    store_generated(store_key, content)

    result = {
        "saved": str(file_path),
        "filename": store_key,
        "size_chars": len(content),
    }

    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(result, indent=2),
            }
        ],
    }
