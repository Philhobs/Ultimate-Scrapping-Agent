"""manage_results MCP tool — store, retrieve, and list intermediate pipeline results."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from api_integrator.state import store_result, get_result, list_results, clear_results


@tool(
    "manage_results",
    "Manage intermediate results for multi-step pipelines. "
    "Actions: 'store' (save a result with a key), 'get' (retrieve by key), "
    "'list' (show all stored keys), 'clear' (remove all stored results).",
    {"action": str, "key": str, "value": str},
)
async def manage_results(args: dict[str, Any]) -> dict[str, Any]:
    action = args.get("action", "list")

    if action == "store":
        key = args.get("key")
        value = args.get("value")
        if not key or value is None:
            return {
                "content": [{"type": "text", "text": "Error: 'key' and 'value' are required for 'store'."}],
                "is_error": True,
            }
        # Try to parse as JSON if possible
        try:
            parsed = json.loads(value)
            store_result(key, parsed)
        except (json.JSONDecodeError, TypeError):
            store_result(key, value)

        return {
            "content": [{"type": "text", "text": f"Stored result under key '{key}'."}],
        }

    if action == "get":
        key = args.get("key")
        if not key:
            return {
                "content": [{"type": "text", "text": "Error: 'key' is required for 'get'."}],
                "is_error": True,
            }
        result = get_result(key)
        if result is None:
            available = list(list_results().keys())
            return {
                "content": [{
                    "type": "text",
                    "text": f"No result found for key '{key}'. Available keys: {available}",
                }],
                "is_error": True,
            }

        if isinstance(result, (dict, list)):
            text = json.dumps(result, indent=2)
        else:
            text = str(result)

        return {"content": [{"type": "text", "text": text}]}

    if action == "list":
        results = list_results()
        if not results:
            return {"content": [{"type": "text", "text": "No results stored."}]}
        return {
            "content": [{"type": "text", "text": json.dumps(results, indent=2)}],
        }

    if action == "clear":
        clear_results()
        return {"content": [{"type": "text", "text": "All stored results cleared."}]}

    return {
        "content": [{
            "type": "text",
            "text": f"Unknown action '{action}'. Use: store, get, list, or clear.",
        }],
        "is_error": True,
    }
