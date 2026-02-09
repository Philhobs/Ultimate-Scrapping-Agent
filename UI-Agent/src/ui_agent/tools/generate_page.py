"""generate_page MCP tool — generate a full page/screen layout."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from ui_agent.state import store_generated, get_design_context


@tool(
    "generate_page",
    "Generate a full page or screen layout. Provide 'description' of the page, "
    "optional 'components' (comma-separated list of component names to include), "
    "and 'framework' (html or react, default html). Optional 'title' for the page.",
    {"description": str, "components": str, "framework": str, "title": str},
)
async def generate_page(args: dict[str, Any]) -> dict[str, Any]:
    description = args.get("description", "")
    components = args.get("components", "")
    framework = args.get("framework", "html")
    title = args.get("title", "Page")

    if not description:
        return {
            "content": [{"type": "text", "text": "Error: 'description' is required."}],
            "is_error": True,
        }

    component_list = [c.strip() for c in components.split(",") if c.strip()] if components else []
    context = get_design_context()

    result = {
        "page_title": title,
        "description": description,
        "framework": framework,
        "components_included": component_list,
        "code": "",
        "filename": "",
    }

    if framework == "react":
        code = _react_page_scaffold(title, description, component_list, context)
        filename = f"{title.replace(' ', '')}.jsx"
    else:
        code = _html_page_scaffold(title, description, component_list, context)
        filename = f"{title.lower().replace(' ', '-')}.html"

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


def _html_page_scaffold(
    title: str, description: str, components: list[str], context: dict,
) -> str:
    """Generate an HTML/Tailwind page scaffold."""
    colors = context.get("design_tokens", {}).get("colors", {})
    primary = colors.get("primary", "#3B82F6")

    component_sections = ""
    for comp in components:
        slug = comp.lower().replace(" ", "-")
        component_sections += f"""
      <!-- {comp} -->
      <section class="{slug} mb-8">
        <h2 class="text-xl font-semibold text-gray-800 mb-4">{comp}</h2>
        <!-- TODO: Insert {comp} component -->
      </section>
"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="min-h-screen bg-gray-50 text-gray-900">
  <!-- Header -->
  <header class="bg-white shadow-sm border-b border-gray-200">
    <nav class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
      <h1 class="text-xl font-bold" style="color: {primary}">{title}</h1>
      <div class="flex items-center gap-4">
        <!-- Navigation items -->
      </div>
    </nav>
  </header>

  <!-- Main Content -->
  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
    <!-- Page: {description} -->
{component_sections}
  </main>

  <!-- Footer -->
  <footer class="bg-white border-t border-gray-200 mt-auto">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 text-center text-gray-500 text-sm">
      &copy; 2024 {title}. All rights reserved.
    </div>
  </footer>
</body>
</html>
"""


def _react_page_scaffold(
    title: str, description: str, components: list[str], context: dict,
) -> str:
    """Generate a React/JSX page scaffold."""
    pascal_name = "".join(word.capitalize() for word in title.replace("-", " ").replace("_", " ").split())

    imports = ""
    component_jsx = ""
    for comp in components:
        comp_pascal = "".join(word.capitalize() for word in comp.replace("-", " ").replace("_", " ").split())
        imports += f"// import {comp_pascal} from './components/{comp_pascal}';\n"
        component_jsx += f"""
        {{/* {comp} */}}
        <section className="mb-8">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">{comp}</h2>
          {{/* <{comp_pascal} /> */}}
        </section>
"""

    return f"""{imports}
/**
 * {pascal_name} — {description}
 */
export default function {pascal_name}() {{
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900">
      {{/* Header */}}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <h1 className="text-xl font-bold text-blue-600">{title}</h1>
          <div className="flex items-center gap-4">
            {{/* Navigation items */}}
          </div>
        </nav>
      </header>

      {{/* Main Content */}}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
{component_jsx}
      </main>

      {{/* Footer */}}
      <footer className="bg-white border-t border-gray-200 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 text-center text-gray-500 text-sm">
          &copy; 2024 {title}. All rights reserved.
        </div>
      </footer>
    </div>
  );
}}
"""
