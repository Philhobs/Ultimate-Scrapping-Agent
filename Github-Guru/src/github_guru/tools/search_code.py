"""search_code MCP tool — regex search across repository files."""

from __future__ import annotations

import fnmatch
import json
import re
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

from github_guru.state import get_analysis, get_repo_root

MAX_RESULTS = 50
CONTEXT_LINES = 2


@tool(
    "search_code",
    "Search for a regex pattern across files in the repository. "
    "Returns matching lines with surrounding context. Optional glob filter for file paths.",
    {"pattern": str, "file_glob": str, "max_results": int},
)
async def search_code(args: dict[str, Any]) -> dict[str, Any]:
    analysis = get_analysis()
    repo_root = get_repo_root()
    pattern = args["pattern"]
    file_glob = args.get("file_glob", "*")
    max_results = args.get("max_results", MAX_RESULTS)

    try:
        regex = re.compile(pattern, re.IGNORECASE)
    except re.error as e:
        return {
            "content": [{"type": "text", "text": f"Invalid regex: {e}"}],
            "is_error": True,
        }

    results = []
    for fi in analysis.files:
        if not fnmatch.fnmatch(fi.filepath, file_glob):
            continue

        try:
            content = (Path(repo_root) / fi.filepath).read_text(errors="replace")
        except OSError:
            continue

        lines = content.split("\n")
        for i, line in enumerate(lines):
            if regex.search(line):
                start = max(0, i - CONTEXT_LINES)
                end = min(len(lines), i + CONTEXT_LINES + 1)
                context = []
                for j in range(start, end):
                    prefix = ">>>" if j == i else "   "
                    context.append(f"{prefix} {j + 1:4d} | {lines[j]}")

                results.append({
                    "file": fi.filepath,
                    "line": i + 1,
                    "match": line.strip(),
                    "context": "\n".join(context),
                })

                if len(results) >= max_results:
                    break

        if len(results) >= max_results:
            break

    summary = f"Found {len(results)} match(es) for pattern '{pattern}'"
    if len(results) >= max_results:
        summary += f" (limited to {max_results})"

    output = {"summary": summary, "matches": results}
    return {
        "content": [{
            "type": "text",
            "text": json.dumps(output, indent=2),
        }]
    }
