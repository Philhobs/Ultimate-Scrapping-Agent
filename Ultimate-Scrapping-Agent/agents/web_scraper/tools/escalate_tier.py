"""MCP tool: escalate_tier — Manual tier control."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from agents.web_scraper.scraping import Tier
from agents.web_scraper.tools.fetch_url import get_tier_manager


@tool(
    "escalate_tier",
    "Manual control over the scraping tier. Actions: "
    "'escalate' (move up one tier), 'set' (set to specific tier 1-4), "
    "'reset' (back to tier 1), 'status' (show current state).",
    {
        "action": str,
        "tier": int,
    },
)
async def escalate_tier_tool(args: dict[str, Any]) -> dict[str, Any]:
    action: str = args.get("action", "status")
    tier_value: int | None = args.get("tier")

    tier_mgr = get_tier_manager()

    try:
        if action == "escalate":
            new_tier = tier_mgr.escalate()
            msg = f"Escalated to tier {new_tier.value} ({new_tier.name})"
        elif action == "set":
            if tier_value is None:
                return {
                    "content": [
                        {"type": "text", "text": "Error: 'set' action requires 'tier' parameter"}
                    ],
                    "is_error": True,
                }
            tier_mgr.set_tier(Tier(tier_value))
            msg = f"Set to tier {tier_value} ({Tier(tier_value).name})"
        elif action == "reset":
            tier_mgr.reset()
            msg = "Reset to tier 1 (BASIC)"
        elif action == "status":
            msg = "Current tier status"
        else:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: Unknown action '{action}'. "
                        "Use: escalate, set, reset, status",
                    }
                ],
                "is_error": True,
            }
    except (RuntimeError, ValueError) as exc:
        return {
            "content": [{"type": "text", "text": f"Error: {exc}"}],
            "is_error": True,
        }

    output = {"message": msg, "status": tier_mgr.status()}
    return {"content": [{"type": "text", "text": json.dumps(output)}]}
