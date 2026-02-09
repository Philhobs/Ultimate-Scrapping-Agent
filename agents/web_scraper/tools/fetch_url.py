"""MCP tool: fetch_url — Fetch a URL with tiered escalation."""

from __future__ import annotations

import json
from typing import Any

from claude_agent_sdk import tool

from agents.web_scraper.scraping import Tier, TierManager, fetch_with_escalation

# Module-level tier manager shared across tool invocations within a session
_tier_manager: TierManager | None = None

MAX_BODY_CHARS = 50_000


def get_tier_manager(max_tier: int = 3, attempts_per_tier: int = 2) -> TierManager:
    """Get or create the session-level TierManager."""
    global _tier_manager
    if _tier_manager is None:
        _tier_manager = TierManager(max_tier=max_tier, attempts_per_tier=attempts_per_tier)
    return _tier_manager


def reset_tier_manager() -> None:
    """Reset the session-level TierManager."""
    global _tier_manager
    _tier_manager = None


@tool(
    "fetch_url",
    "Fetch a web page URL with automatic tier escalation. Starts with basic HTTP, "
    "escalates to stealth headers, headless browser, or proxy if blocked. "
    "Returns the HTML body, status code, tier used, and block detection status.",
    {
        "url": str,
        "cookies": str,
        "force_tier": int,
        "max_tier": int,
    },
)
async def fetch_url_tool(args: dict[str, Any]) -> dict[str, Any]:
    url: str = args["url"]
    cookies_raw: str = args.get("cookies", "")
    force_tier: int | None = args.get("force_tier")
    max_tier: int = args.get("max_tier", 3)

    # Parse cookies from string "key=val; key2=val2"
    cookies: dict[str, str] | None = None
    if cookies_raw:
        cookies = {}
        for part in cookies_raw.split(";"):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                cookies[k.strip()] = v.strip()

    tier_mgr = get_tier_manager(max_tier=max_tier)

    forced = Tier(force_tier) if force_tier else None

    try:
        result = await fetch_with_escalation(
            url=url,
            tier_manager=tier_mgr,
            cookies=cookies,
            force_tier=forced,
        )
    except Exception as exc:
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({
                        "error": str(exc),
                        "url": url,
                        "tier_status": tier_mgr.status(),
                    }),
                }
            ],
            "is_error": True,
        }

    # Truncate body to avoid overwhelming the context
    body = result.html
    truncated = len(body) > MAX_BODY_CHARS
    if truncated:
        body = body[:MAX_BODY_CHARS] + "\n... [TRUNCATED]"

    output = {
        "url": result.url,
        "status_code": result.status_code,
        "tier_used": result.tier,
        "tier_name": Tier(result.tier).name,
        "blocked": result.error is not None,
        "error": result.error,
        "truncated": truncated,
        "body_length": len(result.html),
        "body": body,
    }

    return {"content": [{"type": "text", "text": json.dumps(output)}]}
