"""MCP tool: write_file — Write or update a source code file."""

from __future__ import annotations

import os
from pathlib import Path

from claude_agent_sdk import tool

from orchestrator_agent import state


@tool(
    "write_file",
    "Write or update a source code file in the project directory. "
    "Provide 'rel_path' (relative to project root) and 'content' (full file content).",
    {"rel_path": str, "content": str},
)
def write_file(rel_path: str, content: str) -> dict:
    plan = state.get_plan()
    out = state.get_output_dir()
    project_dir = os.path.join(out, plan["project_name"])
    full_path = os.path.join(project_dir, rel_path)

    Path(full_path).parent.mkdir(parents=True, exist_ok=True)
    Path(full_path).write_text(content)
    state.store_file(rel_path, content)

    return {
        "content": [
            {
                "type": "text",
                "text": f"Wrote {len(content)} chars to {rel_path}",
            }
        ]
    }
