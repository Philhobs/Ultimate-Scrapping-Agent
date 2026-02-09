"""Tier 3: Playwright headless browser client."""

from __future__ import annotations

import asyncio
from typing import ClassVar

from agents.web_scraper.scraping.http_client import FetchResult
from agents.web_scraper.scraping.user_agents import get_random_ua


class BrowserPool:
    """Singleton managing a pool of Playwright browser instances."""

    _instance: ClassVar[BrowserPool | None] = None
    _lock: ClassVar[asyncio.Lock] = asyncio.Lock()

    def __init__(self) -> None:
        self._playwright = None
        self._browser = None

    @classmethod
    async def get_instance(cls) -> BrowserPool:
        async with cls._lock:
            if cls._instance is None:
                cls._instance = BrowserPool()
                await cls._instance._init()
            return cls._instance

    async def _init(self) -> None:
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )

    async def new_page(self):
        if self._browser is None:
            await self._init()
        context = await self._browser.new_context(
            user_agent=get_random_ua(),
            viewport={"width": 1920, "height": 1080},
            java_script_enabled=True,
        )
        return await context.new_page()

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        BrowserPool._instance = None


async def fetch_browser(
    url: str,
    timeout: float = 30.0,
    wait_for: str | None = None,
) -> FetchResult:
    """Tier 3: Fetch page using Playwright headless browser.

    Args:
        url: Target URL to fetch.
        timeout: Navigation timeout in seconds.
        wait_for: Optional CSS selector to wait for before capturing content.
    """
    pool = await BrowserPool.get_instance()
    page = await pool.new_page()
    try:
        response = await page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")
        if wait_for:
            await page.wait_for_selector(wait_for, timeout=timeout * 1000)

        # Allow JS to render
        await page.wait_for_timeout(1000)

        html = await page.content()
        status_code = response.status if response else 200

        return FetchResult(
            url=page.url,
            status_code=status_code,
            html=html,
            headers=dict(response.headers) if response else {},
            tier=3,
        )
    finally:
        await page.close()
