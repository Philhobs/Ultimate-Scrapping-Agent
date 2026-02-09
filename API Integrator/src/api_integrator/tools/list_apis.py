"""list_apis MCP tool — show all registered APIs and their endpoints."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from api_integrator.state import get_api_registry


@tool(
    "list_apis",
    "List all registered APIs with their base URLs, descriptions, and available endpoints.",
    {},
)
async def list_apis(args: dict[str, Any]) -> dict[str, Any]:
    registry = get_api_registry()
    apis = registry.summary()

    if not apis:
        return {"content": [{"type": "text", "text": "No APIs registered."}]}

    return {
        "content": [{
            "type": "text",
            "text": json.dumps(apis, indent=2),
        }]
    }
