"""MCP tool: parse_html — Extract structured data from HTML."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from agents.web_scraper.parsing.html_cleaner import (
    extract_elements,
    extract_links,
    extract_tables,
    extract_text,
)


@tool(
    "parse_html",
    "Parse HTML content and extract structured data. Supports modes: "
    "'text' (clean text), 'links' (all hyperlinks), 'tables' (tabular data), "
    "'elements' (CSS selector match). Use the 'selector' param to scope extraction.",
    {
        "html": str,
        "mode": str,
        "selector": str,
        "attributes": str,
    },
)
async def parse_html_tool(args: dict[str, Any]) -> dict[str, Any]:
    html: str = args["html"]
    mode: str = args.get("mode", "text")
    selector: str | None = args.get("selector")
    attributes_raw: str = args.get("attributes", "")

    attributes = [a.strip() for a in attributes_raw.split(",") if a.strip()] or None

    if mode == "text":
        result = extract_text(html, selector=selector)
    elif mode == "links":
        result = extract_links(html, selector=selector)
    elif mode == "tables":
        result = extract_tables(html, selector=selector)
    elif mode == "elements":
        if not selector:
            return {
                "content": [
                    {"type": "text", "text": "Error: 'elements' mode requires a 'selector' param"}
                ],
                "is_error": True,
            }
        result = extract_elements(html, selector=selector, attributes=attributes)
    else:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Error: Unknown mode '{mode}'. Use: text, links, tables, elements",
                }
            ],
            "is_error": True,
        }

    output = {"mode": mode, "selector": selector, "data": result}
    return {"content": [{"type": "text", "text": json.dumps(output, default=str)}]}
