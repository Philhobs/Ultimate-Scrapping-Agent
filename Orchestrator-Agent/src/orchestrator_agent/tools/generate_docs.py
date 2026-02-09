"""MCP tool: generate_docs — Generate project documentation."""

from __future__ import annotations

import os
from pathlib import Path

from claude_agent_sdk import tool

from orchestrator_agent import state


def _build_readme(plan: dict, files: dict[str, str]) -> str:
    name = plan["project_name"]
    desc = plan.get("description", "")
    stack = plan.get("tech_stack", {})
    milestones = plan.get("milestones", [])

    sections = [
        f"# {name}\n",
        f"{desc}\n",
        "## Tech Stack\n",
    ]
    for category, items in stack.items():
        sections.append(f"- **{category}**: {', '.join(items)}")
    sections.append("")

    sections.append("## Project Structure\n")
    sections.append("```")
    for fpath in sorted(files.keys()):
        sections.append(fpath)
    sections.append("```\n")

    if milestones:
        sections.append("## Development Milestones\n")
        for m in milestones:
            sections.append(f"### Phase {m['phase']}: {m['name']}")
            sections.append(f"{m['description']}\n")
            for d in m.get("deliverables", []):
                sections.append(f"- [ ] {d}")
            sections.append("")

    sections.append("## Getting Started\n")
    lang = plan.get("language", "python")
    if lang == "python":
        sections.extend([
            "```bash",
            "pip install -e .",
            f"python -m {name.replace('-', '_')}",
            "```\n",
        ])
    elif lang in ("typescript", "javascript"):
        sections.extend([
            "```bash",
            "npm install",
            "npm run dev",
            "```\n",
        ])
    elif lang == "go":
        sections.extend([
            "```bash",
            "go build ./...",
            "go run cmd/server/main.go",
            "```\n",
        ])

    sections.append("## License\n\nMIT\n")
    return "\n".join(sections)


def _build_api_docs(files: dict[str, str]) -> str:
    lines = ["# API Documentation\n"]
    for fpath, content in sorted(files.items()):
        if "route" in fpath.lower() or "handler" in fpath.lower():
            lines.append(f"## `{fpath}`\n")
            lines.append("```")
            lines.append(content[:2000])
            lines.append("```\n")
    if len(lines) == 1:
        lines.append("No route/handler files found yet.\n")
    return "\n".join(lines)


@tool(
    "generate_docs",
    "Generate project documentation: README.md, API docs, and usage guide. "
    "Writes files to the project directory. "
    "Optional 'doc_type': 'readme', 'api', or 'all' (default 'all').",
    {"doc_type": str},
)
def generate_docs(doc_type: str = "all") -> dict:
    plan = state.get_plan()
    out = state.get_output_dir()
    project_dir = os.path.join(out, plan["project_name"])
    files = state.get_all_files()
    generated: list[str] = []

    if doc_type in ("readme", "all"):
        readme = _build_readme(plan, files)
        readme_path = os.path.join(project_dir, "README.md")
        Path(readme_path).parent.mkdir(parents=True, exist_ok=True)
        Path(readme_path).write_text(readme)
        state.store_file("README.md", readme)
        generated.append("README.md")

    if doc_type in ("api", "all"):
        api_docs = _build_api_docs(files)
        docs_dir = os.path.join(project_dir, "docs")
        os.makedirs(docs_dir, exist_ok=True)
        api_path = os.path.join(docs_dir, "API.md")
        Path(api_path).write_text(api_docs)
        state.store_file("docs/API.md", api_docs)
        generated.append("docs/API.md")

    return {
        "content": [
            {
                "type": "text",
                "text": (
                    f"Generated documentation:\n"
                    + "\n".join(f"  - {f}" for f in generated)
                ),
            }
        ]
    }
