"""Tier 4: Proxy rotation pool (opt-in)."""

from __future__ import annotations

import itertools

import httpx

from agents.web_scraper.scraping.http_client import FetchResult
from agents.web_scraper.scraping.user_agents import get_random_ua
from common.retry import async_retry


class ProxyPool:
    """Round-robin proxy rotation pool."""

    def __init__(self, proxy_urls: list[str]) -> None:
        if not proxy_urls:
            raise ValueError("ProxyPool requires at least one proxy URL")
        self._proxies = proxy_urls
        self._cycle = itertools.cycle(proxy_urls)

    def next(self) -> str:
        """Get the next proxy URL in rotation."""
        return next(self._cycle)

    @property
    def size(self) -> int:
        return len(self._proxies)


_pool: ProxyPool | None = None


def init_proxy_pool(proxy_urls: list[str]) -> ProxyPool:
    """Initialize the global proxy pool."""
    global _pool
    _pool = ProxyPool(proxy_urls)
    return _pool


def get_proxy_pool() -> ProxyPool | None:
    """Get the global proxy pool, if initialized."""
    return _pool


@async_retry(max_attempts=3)
async def fetch_with_proxy(
    url: str,
    timeout: float = 30.0,
    cookies: dict[str, str] | None = None,
) -> FetchResult:
    """Tier 4: Fetch via rotating proxy with stealth headers.

    Args:
        url: Target URL to fetch.
        timeout: Request timeout in seconds.
        cookies: Optional cookies to include.
    """
    if _pool is None:
        raise RuntimeError("Proxy pool not initialized. Call init_proxy_pool() first.")

    proxy_url = _pool.next()
    headers = {
        "User-Agent": get_random_ua(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
    }

    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        proxy=proxy_url,
    ) as client:
        response = await client.get(url, headers=headers, cookies=cookies)
        return FetchResult(
            url=str(response.url),
            status_code=response.status_code,
            html=response.text,
            headers=dict(response.headers),
            tier=4,
        )
