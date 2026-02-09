"""list_files MCP tool — list files in the analyzed repo."""

from __future__ import annotations

import fnmatch
import json
from typing import Any

from claude_agent_sdk import tool

from github_guru.state import get_analysis


@tool(
    "list_files",
    "List files in the repository. Optionally filter by glob pattern. "
    "Returns file paths with optional metadata (size, language, line count).",
    {"pattern": str, "include_metadata": bool},
)
async def list_files(args: dict[str, Any]) -> dict[str, Any]:
    analysis = get_analysis()
    pattern = args.get("pattern", "*")
    include_metadata = args.get("include_metadata", False)

    results = []
    for fi in analysis.files:
        if not fnmatch.fnmatch(fi.filepath, pattern):
            continue
        if include_metadata:
            results.append({
                "path": fi.filepath,
                "language": fi.language.value,
                "size_bytes": fi.size_bytes,
                "line_count": fi.line_count,
            })
        else:
            results.append(fi.filepath)

    return {
        "content": [{
            "type": "text",
            "text": json.dumps(results, indent=2),
        }]
    }
