"""Tier 1-2: httpx-based async HTTP client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from agents.web_scraper.scraping.user_agents import get_random_ua
from common.retry import async_retry


@dataclass
class FetchResult:
    """Result of an HTTP fetch operation."""

    url: str
    status_code: int
    html: str
    headers: dict[str, str]
    tier: int
    error: str | None = None


@async_retry(max_attempts=2)
async def fetch_basic(
    url: str,
    timeout: float = 30.0,
) -> FetchResult:
    """Tier 1: Plain HTTP GET with minimal headers.

    Args:
        url: Target URL to fetch.
        timeout: Request timeout in seconds.
    """
    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
    ) as client:
        response = await client.get(url)
        return FetchResult(
            url=str(response.url),
            status_code=response.status_code,
            html=response.text,
            headers=dict(response.headers),
            tier=1,
        )


@async_retry(max_attempts=2)
async def fetch_stealth(
    url: str,
    timeout: float = 30.0,
    cookies: dict[str, str] | None = None,
    extra_headers: dict[str, str] | None = None,
) -> FetchResult:
    """Tier 2: HTTP GET with realistic headers, UA rotation, and optional cookies.

    Args:
        url: Target URL to fetch.
        timeout: Request timeout in seconds.
        cookies: Optional cookies to include.
        extra_headers: Additional headers to merge in.
    """
    headers: dict[str, Any] = {
        "User-Agent": get_random_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }
    if extra_headers:
        headers.update(extra_headers)

    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        http2=True,
    ) as client:
        response = await client.get(url, headers=headers, cookies=cookies)
        return FetchResult(
            url=str(response.url),
            status_code=response.status_code,
            html=response.text,
            headers=dict(response.headers),
            tier=2,
        )
