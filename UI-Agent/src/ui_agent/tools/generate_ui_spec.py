"""generate_ui_spec MCP tool — generate a structured JSON UI spec from a description."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from ui_agent.state import set_design_context


@tool(
    "generate_ui_spec",
    "Generate a structured JSON UI specification from a text description. "
    "The spec includes layout structure, component list, design tokens "
    "(colors, typography, spacing), responsive breakpoints, and accessibility notes. "
    "Provide 'description' of the desired UI. Optional: 'framework' (html or react).",
    {"description": str, "framework": str},
)
async def generate_ui_spec(args: dict[str, Any]) -> dict[str, Any]:
    description = args.get("description", "")
    framework = args.get("framework", "html")

    if not description:
        return {
            "content": [{"type": "text", "text": "Error: 'description' is required."}],
            "is_error": True,
        }

    spec = {
        "description": description,
        "framework": framework,
        "layout": {
            "type": "single-page",
            "sections": [],
            "grid_system": "flexbox",
        },
        "components": [],
        "design_tokens": {
            "colors": {
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
            },
            "typography": {
                "font_family": "Inter, system-ui, sans-serif",
                "scale": {
                    "xs": "0.75rem",
                    "sm": "0.875rem",
                    "base": "1rem",
                    "lg": "1.125rem",
                    "xl": "1.25rem",
                    "2xl": "1.5rem",
                    "3xl": "1.875rem",
                    "4xl": "2.25rem",
                },
            },
            "spacing": {
                "unit": "0.25rem",
                "scale": [0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24],
            },
            "border_radius": {
                "sm": "0.25rem",
                "md": "0.375rem",
                "lg": "0.5rem",
                "xl": "0.75rem",
                "full": "9999px",
            },
        },
        "breakpoints": {
            "sm": "640px",
            "md": "768px",
            "lg": "1024px",
            "xl": "1280px",
        },
        "accessibility": {
            "semantic_html": True,
            "aria_labels": True,
            "keyboard_navigation": True,
            "color_contrast": "WCAG AA",
            "focus_indicators": True,
        },
    }

    set_design_context(spec)

    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(spec, indent=2),
            }
        ],
    }
