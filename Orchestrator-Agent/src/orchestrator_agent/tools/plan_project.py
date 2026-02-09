"""MCP tool: plan_project — Analyze requirements and create a project plan."""

from __future__ import annotations

from claude_agent_sdk import tool

from orchestrator_agent.analyzers.project_planner import create_project_plan
from orchestrator_agent import state


@tool(
    "plan_project",
    "Analyze a project description and produce a structured plan: "
    "architecture, tech stack, file structure, milestones, and dependencies. "
    "Must be called first before scaffolding or coding. "
    "Provide 'description' (requirements) and optional 'project_name'.",
    {"description": str, "project_name": str},
)
def plan_project(description: str, project_name: str = "my-project") -> dict:
    plan = create_project_plan(description, project_name)
    state.set_plan(plan)
    return {
        "content": [
            {
                "type": "text",
                "text": (
                    f"Project plan created for '{project_name}' "
                    f"({plan['project_type']} / {plan['language']}).\n\n"
                    f"Tech stack: {plan['tech_stack']}\n\n"
                    f"Files ({len(plan['file_structure'])}): "
                    f"{', '.join(plan['file_structure'][:10])}"
                    f"{'...' if len(plan['file_structure']) > 10 else ''}\n\n"
                    f"Milestones: {len(plan['milestones'])} phases"
                ),
            }
        ]
    }
