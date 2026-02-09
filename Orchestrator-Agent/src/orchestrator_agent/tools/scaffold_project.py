"""MCP tool: scaffold_project — Create the project directory structure."""

from __future__ import annotations

import os
from pathlib import Path

from claude_agent_sdk import tool

from orchestrator_agent import state


@tool(
    "scaffold_project",
    "Create the project directory structure with boilerplate files "
    "based on the plan's tech stack and project type. "
    "Requires plan_project to have been called first. "
    "Optional 'output_dir' overrides the default output directory.",
    {"output_dir": str},
)
def scaffold_project(output_dir: str = "") -> dict:
    plan = state.get_plan()
    out = output_dir or state.get_output_dir()
    state.set_output_dir(out)

    project_dir = os.path.join(out, plan["project_name"])
    created: list[str] = []

    for rel_path in plan["file_structure"]:
        full_path = os.path.join(project_dir, rel_path)
        Path(full_path).parent.mkdir(parents=True, exist_ok=True)
        if not os.path.exists(full_path):
            Path(full_path).write_text("")
            created.append(rel_path)

    return {
        "content": [
            {
                "type": "text",
                "text": (
                    f"Scaffolded project at {project_dir}\n"
                    f"Created {len(created)} files:\n"
                    + "\n".join(f"  - {f}" for f in created)
                ),
            }
        ]
    }
