"""Tests for HTTP client (Tier 1-2) with mocked responses."""

from __future__ import annotations

import pytest
import httpx
import respx

from agents.web_scraper.scraping.http_client import fetch_basic, fetch_stealth


@respx.mock
@pytest.mark.asyncio
async def test_fetch_basic_success():
    respx.get("https://example.com/").mock(
        return_value=httpx.Response(200, text="<html><body>Hello</body></html>")
    )
    result = await fetch_basic("https://example.com/")
    assert result.status_code == 200
    assert result.tier == 1
    assert "Hello" in result.html
    assert result.error is None


@respx.mock
@pytest.mark.asyncio
async def test_fetch_basic_404():
    respx.get("https://example.com/missing").mock(
        return_value=httpx.Response(404, text="Not Found")
    )
    result = await fetch_basic("https://example.com/missing")
    assert result.status_code == 404
    assert result.tier == 1


@respx.mock
@pytest.mark.asyncio
async def test_fetch_stealth_success():
    respx.get("https://example.com/").mock(
        return_value=httpx.Response(200, text="<html><body>Stealth</body></html>")
    )
    result = await fetch_stealth("https://example.com/")
    assert result.status_code == 200
    assert result.tier == 2
    assert "Stealth" in result.html


@respx.mock
@pytest.mark.asyncio
async def test_fetch_stealth_with_cookies():
    respx.get("https://example.com/").mock(
        return_value=httpx.Response(200, text="<html>OK</html>")
    )
    result = await fetch_stealth(
        "https://example.com/",
        cookies={"session": "abc123"},
    )
    assert result.status_code == 200
    assert result.tier == 2
