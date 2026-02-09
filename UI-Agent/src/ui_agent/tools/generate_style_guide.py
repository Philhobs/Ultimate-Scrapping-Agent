"""generate_style_guide MCP tool — generate design system documentation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from claude_agent_sdk import tool

from ui_agent.state import store_generated, get_design_context, get_output_dir


@tool(
    "generate_style_guide",
    "Generate design system documentation including colors, typography, spacing, "
    "component catalog, and usage guidelines. Optional 'name' for the design system. "
    "Optional 'format' (markdown or html, default markdown).",
    {"name": str, "format": str},
)
async def generate_style_guide(args: dict[str, Any]) -> dict[str, Any]:
    name = args.get("name", "Design System")
    output_format = args.get("format", "markdown")

    context = get_design_context()
    tokens = context.get("design_tokens", {})

    colors = tokens.get("colors", {
        "primary": "#3B82F6",
        "secondary": "#6366F1",
        "accent": "#F59E0B",
        "background": "#FFFFFF",
        "surface": "#F9FAFB",
        "text_primary": "#111827",
        "text_secondary": "#6B7280",
        "border": "#E5E7EB",
        "error": "#EF4444",
        "success": "#10B981",
    })

    typography = tokens.get("typography", {
        "font_family": "Inter, system-ui, sans-serif",
        "scale": {
            "xs": "0.75rem", "sm": "0.875rem", "base": "1rem",
            "lg": "1.125rem", "xl": "1.25rem", "2xl": "1.5rem",
            "3xl": "1.875rem", "4xl": "2.25rem",
        },
    })

    spacing = tokens.get("spacing", {
        "unit": "0.25rem",
        "scale": [0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24],
    })

    if output_format == "html":
        content = _generate_html_guide(name, colors, typography, spacing)
        filename = "style-guide.html"
    else:
        content = _generate_markdown_guide(name, colors, typography, spacing)
        filename = "style-guide.md"

    # Save to output dir
    out = Path(get_output_dir())
    out.mkdir(parents=True, exist_ok=True)
    (out / filename).write_text(content)
    store_generated(filename, content)

    result = {
        "filename": filename,
        "format": output_format,
        "output_path": str(out / filename),
        "length_chars": len(content),
    }

    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(result, indent=2),
            }
        ],
    }


def _generate_markdown_guide(name: str, colors: dict, typography: dict, spacing: dict) -> str:
    """Generate a Markdown style guide."""
    lines = [
        f"# {name}",
        "",
        "## Colors",
        "",
        "| Token | Value | Usage |",
        "|-------|-------|-------|",
    ]

    color_usage = {
        "primary": "Main brand color, buttons, links",
        "secondary": "Secondary actions, accents",
        "accent": "Highlights, badges, alerts",
        "background": "Page background",
        "surface": "Card and panel backgrounds",
        "text_primary": "Headings, body text",
        "text_secondary": "Captions, placeholders",
        "border": "Dividers, input borders",
        "error": "Error states, destructive actions",
        "success": "Success states, confirmations",
    }

    for token, value in colors.items():
        usage = color_usage.get(token, "")
        lines.append(f"| `{token}` | `{value}` | {usage} |")

    lines.extend([
        "",
        "## Typography",
        "",
        f"**Font Family:** `{typography.get('font_family', 'system-ui')}`",
        "",
        "### Scale",
        "",
        "| Size | Value |",
        "|------|-------|",
    ])

    for size, value in typography.get("scale", {}).items():
        lines.append(f"| `{size}` | `{value}` |")

    lines.extend([
        "",
        "## Spacing",
        "",
        f"**Base unit:** `{spacing.get('unit', '0.25rem')}`",
        "",
        "| Step | Value |",
        "|------|-------|",
    ])

    unit_val = 4  # 0.25rem = 4px
    for step in spacing.get("scale", []):
        px = step * unit_val
        lines.append(f"| `{step}` | `{px}px` / `{step * 0.25}rem` |")

    lines.extend([
        "",
        "## Components",
        "",
        "### Buttons",
        "- Primary: `bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700`",
        "- Secondary: `bg-gray-200 text-gray-800 px-4 py-2 rounded-lg hover:bg-gray-300`",
        "- Outline: `border border-blue-600 text-blue-600 px-4 py-2 rounded-lg hover:bg-blue-50`",
        "",
        "### Inputs",
        "- Text: `border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500`",
        "",
        "### Cards",
        "- Default: `bg-white rounded-xl shadow-sm border border-gray-200 p-6`",
        "",
    ])

    return "\n".join(lines)


def _generate_html_guide(name: str, colors: dict, typography: dict, spacing: dict) -> str:
    """Generate an HTML style guide with visual swatches."""
    color_swatches = ""
    for token, value in colors.items():
        color_swatches += f"""
      <div class="flex items-center gap-3 mb-2">
        <div class="w-10 h-10 rounded-lg border border-gray-200" style="background-color: {value}"></div>
        <div>
          <span class="font-mono text-sm">{token}</span>
          <span class="text-gray-500 text-sm ml-2">{value}</span>
        </div>
      </div>"""

    type_scale = ""
    for size, value in typography.get("scale", {}).items():
        type_scale += f'      <p style="font-size: {value}" class="mb-2"><span class="text-gray-500 text-sm w-16 inline-block">{size}</span> The quick brown fox ({value})</p>\n'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{name}</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 p-8">
  <div class="max-w-4xl mx-auto">
    <h1 class="text-3xl font-bold mb-8">{name}</h1>

    <section class="bg-white rounded-xl shadow-sm border p-6 mb-6">
      <h2 class="text-xl font-semibold mb-4">Colors</h2>
{color_swatches}
    </section>

    <section class="bg-white rounded-xl shadow-sm border p-6 mb-6">
      <h2 class="text-xl font-semibold mb-4">Typography</h2>
      <p class="text-gray-500 mb-4">Font: <code>{typography.get("font_family", "system-ui")}</code></p>
{type_scale}
    </section>

    <section class="bg-white rounded-xl shadow-sm border p-6 mb-6">
      <h2 class="text-xl font-semibold mb-4">Components</h2>
      <div class="space-y-4">
        <div>
          <h3 class="text-sm font-medium text-gray-500 mb-2">Buttons</h3>
          <div class="flex gap-3">
            <button class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">Primary</button>
            <button class="bg-gray-200 text-gray-800 px-4 py-2 rounded-lg hover:bg-gray-300">Secondary</button>
            <button class="border border-blue-600 text-blue-600 px-4 py-2 rounded-lg hover:bg-blue-50">Outline</button>
          </div>
        </div>
        <div>
          <h3 class="text-sm font-medium text-gray-500 mb-2">Inputs</h3>
          <input type="text" placeholder="Text input" class="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500">
        </div>
      </div>
    </section>
  </div>
</body>
</html>
"""
