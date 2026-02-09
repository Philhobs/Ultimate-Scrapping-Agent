"""MCP tool: extract_data — Prepare content for LLM-powered structured extraction."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from agents.web_scraper.parsing.html_cleaner import clean_html


@tool(
    "extract_data",
    "Prepare HTML content for structured data extraction. Cleans the HTML and returns "
    "it with extraction instructions based on the provided JSON schema and output format. "
    "The agent's own reasoning performs the actual extraction — no nested API calls.",
    {
        "html": str,
        "schema_fields": str,
        "output_format": str,
    },
)
async def extract_data_tool(args: dict[str, Any]) -> dict[str, Any]:
    html: str = args["html"]
    schema_fields_raw: str = args.get("schema_fields", "")
    output_format: str = args.get("output_format", "json")

    # Parse schema fields: comma-separated or JSON array
    schema_fields: list[str] = []
    if schema_fields_raw:
        try:
            schema_fields = json.loads(schema_fields_raw)
        except json.JSONDecodeError:
            schema_fields = [f.strip() for f in schema_fields_raw.split(",") if f.strip()]

    # Clean HTML to reduce noise
    soup = clean_html(html)
    cleaned_text = soup.get_text(separator="\n", strip=True)

    # Truncate to keep within context limits
    max_chars = 30_000
    truncated = len(cleaned_text) > max_chars
    if truncated:
        cleaned_text = cleaned_text[:max_chars] + "\n... [TRUNCATED]"

    extraction_prompt = (
        f"Extract the following fields from the content below: {schema_fields}\n"
        f"Output format: {output_format}\n"
        f"---\n"
        f"{cleaned_text}"
    )

    output = {
        "extraction_prompt": extraction_prompt,
        "schema_fields": schema_fields,
        "output_format": output_format,
        "content_length": len(cleaned_text),
        "truncated": truncated,
    }

    return {"content": [{"type": "text", "text": json.dumps(output)}]}
