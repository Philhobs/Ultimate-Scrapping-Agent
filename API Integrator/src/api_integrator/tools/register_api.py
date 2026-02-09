"""register_api MCP tool — dynamically register a new API endpoint."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from api_integrator.state import get_api_registry


@tool(
    "register_api",
    "Register a new API endpoint. Provide a name, base_url, and optionally "
    "a description, auth_type (none/bearer/api_key), and auth_env_var "
    "(environment variable name holding the API key).",
    {
        "name": str,
        "base_url": str,
        "description": str,
        "auth_type": str,
        "auth_env_var": str,
    },
)
async def register_api(args: dict[str, Any]) -> dict[str, Any]:
    registry = get_api_registry()

    name = args["name"]
    base_url = args["base_url"]
    description = args.get("description", "")
    auth_type = args.get("auth_type", "none")
    auth_env_var = args.get("auth_env_var")

    api = registry.register(
        name=name,
        base_url=base_url,
        description=description,
        auth_type=auth_type,
        auth_env_var=auth_env_var,
    )

    return {
        "content": [{
            "type": "text",
            "text": json.dumps({
                "status": "registered",
                "name": api.name,
                "base_url": api.base_url,
                "auth_type": api.auth_type,
            }, indent=2),
        }]
    }
