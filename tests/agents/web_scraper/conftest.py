"""Shared test fixtures for web scraper tests."""

from __future__ import annotations

import pytest

from agents.web_scraper.scraping.tiers import Tier, TierManager


@pytest.fixture
def tier_manager() -> TierManager:
    """Fresh TierManager starting at Tier 1."""
    return TierManager(max_tier=3, attempts_per_tier=2)


@pytest.fixture
def sample_html() -> str:
    """Sample HTML page for parsing tests."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Test Page</title>
    <script>var x = 1;</script>
    <style>body { color: red; }</style>
    </head>
    <body>
        <nav><a href="/home">Home</a></nav>
        <main>
            <h1>Book Store</h1>
            <div class="product">
                <h2 class="title">Book One</h2>
                <span class="price">$10.99</span>
                <a href="/book/1">Details</a>
            </div>
            <div class="product">
                <h2 class="title">Book Two</h2>
                <span class="price">$15.50</span>
                <a href="/book/2">Details</a>
            </div>
            <table>
                <tr><th>Title</th><th>Price</th></tr>
                <tr><td>Book One</td><td>$10.99</td></tr>
                <tr><td>Book Two</td><td>$15.50</td></tr>
            </table>
        </main>
        <footer>Copyright 2024</footer>
    </body>
    </html>
    """


@pytest.fixture
def blocked_html_cloudflare() -> str:
    """HTML that looks like a Cloudflare challenge."""
    return """
    <html>
    <head><title>Just a moment...</title></head>
    <body>
        <div id="cf-browser-verification">
            Checking if the site connection is secure
        </div>
    </body>
    </html>
    """


@pytest.fixture
def blocked_html_captcha() -> str:
    """HTML containing a reCAPTCHA."""
    return """
    <html>
    <body>
        <div class="g-recaptcha" data-sitekey="abc123"></div>
        <script src="https://www.google.com/recaptcha/api.js"></script>
    </body>
    </html>
    """
