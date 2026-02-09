"""Tests for MCP tools and HTML parsing."""

from __future__ import annotations

import json

import pytest

from agents.web_scraper.parsing.html_cleaner import (
    extract_elements,
    extract_links,
    extract_tables,
    extract_text,
)
from agents.web_scraper.scraping.anti_detect import check_blocked


class TestHTMLCleaner:
    def test_extract_text(self, sample_html: str):
        text = extract_text(sample_html)
        assert "Book Store" in text
        assert "Book One" in text
        assert "$10.99" in text
        # Script/style/nav/footer should be removed
        assert "var x = 1" not in text
        assert "body { color: red; }" not in text

    def test_extract_text_with_selector(self, sample_html: str):
        text = extract_text(sample_html, selector=".product")
        assert "Book One" in text
        assert "Book Store" not in text

    def test_extract_text_selector_not_found(self, sample_html: str):
        text = extract_text(sample_html, selector=".nonexistent")
        assert text == ""

    def test_extract_links(self, sample_html: str):
        links = extract_links(sample_html)
        hrefs = [l["href"] for l in links]
        assert "/book/1" in hrefs
        assert "/book/2" in hrefs
        # Nav link should be stripped (nav is removed)
        assert "/home" not in hrefs

    def test_extract_links_with_selector(self, sample_html: str):
        links = extract_links(sample_html, selector="main")
        assert len(links) == 2
        assert links[0]["text"] == "Details"

    def test_extract_tables(self, sample_html: str):
        tables = extract_tables(sample_html)
        assert len(tables) == 1
        table = tables[0]
        assert table[0] == ["Title", "Price"]  # header row
        assert table[1] == ["Book One", "$10.99"]
        assert table[2] == ["Book Two", "$15.50"]

    def test_extract_elements(self, sample_html: str):
        elements = extract_elements(sample_html, selector=".title")
        assert len(elements) == 2
        assert elements[0]["text"] == "Book One"
        assert elements[1]["text"] == "Book Two"

    def test_extract_elements_with_attributes(self, sample_html: str):
        elements = extract_elements(
            sample_html, selector=".price", attributes=["class"]
        )
        assert len(elements) == 2
        assert elements[0]["class"] == ["price"]


class TestAntiDetect:
    def test_not_blocked(self):
        result = check_blocked("<html><body>Normal page</body></html>", 200)
        assert not result.is_blocked

    def test_blocked_403(self):
        result = check_blocked("Forbidden", 403)
        assert result.is_blocked
        assert result.block_type == "http_403"

    def test_blocked_429(self):
        result = check_blocked("Too Many Requests", 429)
        assert result.is_blocked
        assert result.block_type == "rate_limited"

    def test_blocked_cloudflare(self, blocked_html_cloudflare: str):
        result = check_blocked(blocked_html_cloudflare, 200)
        assert result.is_blocked
        assert "cloudflare" in result.block_type

    def test_blocked_recaptcha(self, blocked_html_captcha: str):
        result = check_blocked(blocked_html_captcha, 200)
        assert result.is_blocked
        assert result.block_type == "recaptcha"

    def test_blocked_503_with_cloudflare(self, blocked_html_cloudflare: str):
        result = check_blocked(blocked_html_cloudflare, 503)
        assert result.is_blocked

    def test_503_without_pattern(self):
        result = check_blocked("<html><body>Service Unavailable</body></html>", 503)
        assert not result.is_blocked


class TestParseHTMLTool:
    @pytest.mark.asyncio
    async def test_parse_html_text_mode(self, sample_html: str):
        from agents.web_scraper.tools.parse_html import parse_html_tool

        result = await parse_html_tool.handler({"html": sample_html, "mode": "text"})
        assert not result.get("is_error")
        data = json.loads(result["content"][0]["text"])
        assert "Book Store" in data["data"]

    @pytest.mark.asyncio
    async def test_parse_html_links_mode(self, sample_html: str):
        from agents.web_scraper.tools.parse_html import parse_html_tool

        result = await parse_html_tool.handler({"html": sample_html, "mode": "links"})
        data = json.loads(result["content"][0]["text"])
        hrefs = [l["href"] for l in data["data"]]
        assert "/book/1" in hrefs

    @pytest.mark.asyncio
    async def test_parse_html_tables_mode(self, sample_html: str):
        from agents.web_scraper.tools.parse_html import parse_html_tool

        result = await parse_html_tool.handler({"html": sample_html, "mode": "tables"})
        data = json.loads(result["content"][0]["text"])
        assert len(data["data"]) == 1

    @pytest.mark.asyncio
    async def test_parse_html_elements_mode(self, sample_html: str):
        from agents.web_scraper.tools.parse_html import parse_html_tool

        result = await parse_html_tool.handler({
            "html": sample_html,
            "mode": "elements",
            "selector": ".title",
        })
        data = json.loads(result["content"][0]["text"])
        assert len(data["data"]) == 2

    @pytest.mark.asyncio
    async def test_parse_html_elements_no_selector(self, sample_html: str):
        from agents.web_scraper.tools.parse_html import parse_html_tool

        result = await parse_html_tool.handler({"html": sample_html, "mode": "elements"})
        assert result.get("is_error")

    @pytest.mark.asyncio
    async def test_parse_html_invalid_mode(self, sample_html: str):
        from agents.web_scraper.tools.parse_html import parse_html_tool

        result = await parse_html_tool.handler({"html": sample_html, "mode": "invalid"})
        assert result.get("is_error")


class TestExtractDataTool:
    @pytest.mark.asyncio
    async def test_extract_data_basic(self, sample_html: str):
        from agents.web_scraper.tools.extract_data import extract_data_tool

        result = await extract_data_tool.handler({
            "html": sample_html,
            "schema_fields": "title,price",
            "output_format": "json",
        })
        data = json.loads(result["content"][0]["text"])
        assert data["schema_fields"] == ["title", "price"]
        assert data["output_format"] == "json"
        assert "Book One" in data["extraction_prompt"]

    @pytest.mark.asyncio
    async def test_extract_data_json_schema_fields(self, sample_html: str):
        from agents.web_scraper.tools.extract_data import extract_data_tool

        result = await extract_data_tool.handler({
            "html": sample_html,
            "schema_fields": '["name", "cost"]',
            "output_format": "csv",
        })
        data = json.loads(result["content"][0]["text"])
        assert data["schema_fields"] == ["name", "cost"]


class TestEscalateTierTool:
    @pytest.mark.asyncio
    async def test_status(self):
        from agents.web_scraper.tools.escalate_tier import escalate_tier_tool
        from agents.web_scraper.tools.fetch_url import reset_tier_manager

        reset_tier_manager()
        result = await escalate_tier_tool.handler({"action": "status"})
        data = json.loads(result["content"][0]["text"])
        assert data["status"]["current_tier"] == 1

    @pytest.mark.asyncio
    async def test_escalate(self):
        from agents.web_scraper.tools.escalate_tier import escalate_tier_tool
        from agents.web_scraper.tools.fetch_url import reset_tier_manager

        reset_tier_manager()
        result = await escalate_tier_tool.handler({"action": "escalate"})
        data = json.loads(result["content"][0]["text"])
        assert data["status"]["current_tier"] == 2

    @pytest.mark.asyncio
    async def test_set_tier(self):
        from agents.web_scraper.tools.escalate_tier import escalate_tier_tool
        from agents.web_scraper.tools.fetch_url import reset_tier_manager

        reset_tier_manager()
        result = await escalate_tier_tool.handler({"action": "set", "tier": 3})
        data = json.loads(result["content"][0]["text"])
        assert data["status"]["current_tier"] == 3

    @pytest.mark.asyncio
    async def test_reset(self):
        from agents.web_scraper.tools.escalate_tier import escalate_tier_tool
        from agents.web_scraper.tools.fetch_url import reset_tier_manager

        reset_tier_manager()
        await escalate_tier_tool.handler({"action": "escalate"})
        result = await escalate_tier_tool.handler({"action": "reset"})
        data = json.loads(result["content"][0]["text"])
        assert data["status"]["current_tier"] == 1

    @pytest.mark.asyncio
    async def test_invalid_action(self):
        from agents.web_scraper.tools.escalate_tier import escalate_tier_tool
        from agents.web_scraper.tools.fetch_url import reset_tier_manager

        reset_tier_manager()
        result = await escalate_tier_tool.handler({"action": "invalid"})
        assert result.get("is_error")
