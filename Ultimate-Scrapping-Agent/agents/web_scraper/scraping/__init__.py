"""Tiered scraping infrastructure with auto-escalation."""

from __future__ import annotations

import structlog

from agents.web_scraper.scraping.anti_detect import check_blocked
from agents.web_scraper.scraping.browser_client import fetch_browser
from agents.web_scraper.scraping.http_client import FetchResult, fetch_basic, fetch_stealth
from agents.web_scraper.scraping.proxy_pool import fetch_with_proxy, get_proxy_pool
from agents.web_scraper.scraping.tiers import Tier, TierManager

__all__ = [
    "Tier",
    "TierManager",
    "fetch_basic",
    "fetch_stealth",
    "fetch_browser",
    "fetch_with_proxy",
    "fetch_with_escalation",
    "check_blocked",
]

logger = structlog.get_logger()

_TIER_FETCHERS = {
    Tier.BASIC: lambda url, timeout, **kw: fetch_basic(url, timeout=timeout),
    Tier.STEALTH: lambda url, timeout, **kw: fetch_stealth(
        url, timeout=timeout, cookies=kw.get("cookies")
    ),
    Tier.BROWSER: lambda url, timeout, **kw: fetch_browser(url, timeout=timeout),
    Tier.PROXY: lambda url, timeout, **kw: fetch_with_proxy(
        url, timeout=timeout, cookies=kw.get("cookies")
    ),
}


async def fetch_with_escalation(
    url: str,
    tier_manager: TierManager,
    timeout: float = 30.0,
    cookies: dict[str, str] | None = None,
    force_tier: Tier | None = None,
) -> FetchResult:
    """Fetch a URL with automatic tier escalation on block/failure.

    Tries the current tier, detects blocks, and auto-escalates if possible.

    Args:
        url: Target URL.
        tier_manager: TierManager instance controlling escalation state.
        timeout: Per-request timeout in seconds.
        cookies: Optional cookies to pass to fetchers.
        force_tier: Skip escalation logic and use this tier directly.
    """
    if force_tier is not None:
        tier_manager.set_tier(force_tier)

    while True:
        tier = tier_manager.current_tier

        # Skip proxy tier if no pool configured
        if tier == Tier.PROXY and get_proxy_pool() is None:
            raise RuntimeError(
                "Tier 4 (proxy) requested but no proxy pool configured. "
                "Set AGENT_SCRAPER_PROXY_URLS or reduce max_tier."
            )

        fetcher = _TIER_FETCHERS[tier]
        log = logger.bind(url=url, tier=tier.name)

        try:
            log.info("scraping.fetch.start")
            result = await fetcher(url, timeout=timeout, cookies=cookies)
        except Exception as exc:
            log.warning("scraping.fetch.error", error=str(exc))
            tier_manager.record_attempt(tier)
            if tier_manager.should_escalate() and tier_manager.can_escalate():
                new_tier = tier_manager.escalate()
                log.info("scraping.tier.escalated", new_tier=new_tier.name)
                continue
            raise

        # Check for blocks
        detection = check_blocked(result.html, result.status_code)
        if detection.is_blocked:
            log.warning(
                "scraping.blocked",
                block_type=detection.block_type,
                details=detection.details,
            )
            tier_manager.record_attempt(tier)
            if tier_manager.should_escalate() and tier_manager.can_escalate():
                new_tier = tier_manager.escalate()
                log.info("scraping.tier.escalated", new_tier=new_tier.name, reason="blocked")
                continue
            # Return the blocked result if we can't escalate further
            result.error = f"Blocked: {detection.block_type} - {detection.details}"
            return result

        log.info("scraping.fetch.success", status=result.status_code)
        return result
