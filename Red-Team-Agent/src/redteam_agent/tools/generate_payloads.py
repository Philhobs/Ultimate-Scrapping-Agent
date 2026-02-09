"""generate_payloads MCP tool — generate categorized attack payloads for testing."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from redteam_agent.analyzers.payload_generator import get_payloads_for_category, get_all_payloads


@tool(
    "generate_payloads",
    "Generate categorized test payloads for authorized security testing. "
    "Provide 'category': 'sqli', 'xss', 'cmdi', 'path_traversal', 'ssrf', "
    "'auth', 'prompt_injection', 'fuzz', or 'all'. "
    "These are for testing YOUR OWN systems only.",
    {"category": str},
)
async def generate_payloads(args: dict[str, Any]) -> dict[str, Any]:
    category = args.get("category", "all")

    if category == "all":
        payloads = get_all_payloads()
    else:
        payloads = get_payloads_for_category(category)

    if not payloads:
        return {
            "content": [{"type": "text", "text": f"Unknown category: {category}. "
                         "Use: sqli, xss, cmdi, path_traversal, ssrf, auth, prompt_injection, fuzz, all."}],
            "is_error": True,
        }

    # Group by category
    grouped: dict[str, list[dict]] = {}
    for p in payloads:
        grouped.setdefault(p.category, []).append(p.to_dict())

    result = {
        "category": category,
        "total_payloads": len(payloads),
        "payloads_by_category": {k: len(v) for k, v in grouped.items()},
        "payloads": grouped,
        "disclaimer": "These payloads are for AUTHORIZED testing of your own systems only.",
    }

    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
