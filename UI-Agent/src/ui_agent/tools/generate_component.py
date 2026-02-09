"""generate_component MCP tool — generate a reusable UI component."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from ui_agent.state import store_generated


@tool(
    "generate_component",
    "Generate a reusable UI component. Provide 'name' (component name), "
    "'description' (what it does/looks like), 'framework' (html or react, default html), "
    "and optional 'states' (comma-separated: default, hover, active, disabled, loading).",
    {"name": str, "description": str, "framework": str, "states": str},
)
async def generate_component(args: dict[str, Any]) -> dict[str, Any]:
    name = args.get("name", "")
    description = args.get("description", "")
    framework = args.get("framework", "html")
    states = args.get("states", "default")

    if not name:
        return {
            "content": [{"type": "text", "text": "Error: 'name' is required."}],
            "is_error": True,
        }

    if not description:
        return {
            "content": [{"type": "text", "text": "Error: 'description' is required."}],
            "is_error": True,
        }

    state_list = [s.strip() for s in states.split(",")]

    result = {
        "component_name": name,
        "description": description,
        "framework": framework,
        "states": state_list,
        "code": "",
        "usage_example": "",
    }

    # Generate component scaffold based on framework
    if framework == "react":
        pascal_name = "".join(word.capitalize() for word in name.replace("-", " ").replace("_", " ").split())
        code = _react_component_scaffold(pascal_name, description, state_list)
        filename = f"{pascal_name}.jsx"
    else:
        code = _html_component_scaffold(name, description, state_list)
        filename = f"{name.lower().replace(' ', '-')}.html"

    result["code"] = code
    result["filename"] = filename

    store_generated(filename, code)

    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(result, indent=2),
            }
        ],
    }


def _html_component_scaffold(name: str, description: str, states: list[str]) -> str:
    """Generate an HTML/Tailwind component scaffold."""
    slug = name.lower().replace(" ", "-")
    lines = [
        f"<!-- {name} Component: {description} -->",
        f'<div class="{slug}" role="region" aria-label="{name}">',
        f"  <!-- TODO: Implement {name} -->",
        f'  <div class="p-4 rounded-lg border border-gray-200">',
        f'    <p class="text-gray-700">{name}</p>',
        f"  </div>",
        f"</div>",
    ]

    if "hover" in states:
        lines.append(f"\n<!-- Hover state: add hover:shadow-md hover:border-blue-300 -->")
    if "disabled" in states:
        lines.append(f"\n<!-- Disabled state: add opacity-50 cursor-not-allowed -->")
    if "loading" in states:
        lines.append(f"\n<!-- Loading state: add animate-pulse -->")

    return "\n".join(lines) + "\n"


def _react_component_scaffold(name: str, description: str, states: list[str]) -> str:
    """Generate a React/JSX component scaffold."""
    props = ["className = ''"]
    if "disabled" in states:
        props.append("disabled = false")
    if "loading" in states:
        props.append("loading = false")

    props_str = ", ".join(props)

    lines = [
        f"/**",
        f" * {name} — {description}",
        f" */",
        f"export default function {name}({{ {props_str} }}) {{",
    ]

    if "loading" in states:
        lines.extend([
            f"  if (loading) {{",
            f'    return <div className="animate-pulse p-4 bg-gray-200 rounded-lg" />;',
            f"  }}",
            f"",
        ])

    lines.extend([
        f"  return (",
        f'    <div className={{`p-4 rounded-lg border border-gray-200 ${{className}}`}}>',
        f"      {{{/* TODO: Implement {name} */}}}",
        f'      <p className="text-gray-700">{name}</p>',
        f"    </div>",
        f"  );",
        f"}}",
    ])

    return "\n".join(lines) + "\n"
