"""CAPTCHA and block detection (detect-only, never solve)."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class BlockDetection:
    """Result of anti-bot detection analysis."""

    is_blocked: bool = False
    block_type: str | None = None
    details: str | None = None


# Patterns that indicate bot detection / blocking
_BLOCK_PATTERNS = [
    # Cloudflare
    (r"Checking if the site connection is secure", "cloudflare_challenge"),
    (r"cf-browser-verification", "cloudflare_challenge"),
    (r"cloudflare.*challenge", "cloudflare_challenge"),
    (r"ray ID", "cloudflare_block"),
    # reCAPTCHA
    (r"g-recaptcha", "recaptcha"),
    (r"recaptcha/api", "recaptcha"),
    (r"grecaptcha", "recaptcha"),
    # hCaptcha
    (r"hcaptcha\.com", "hcaptcha"),
    (r"h-captcha", "hcaptcha"),
    # Generic blocks
    (r"Access Denied", "access_denied"),
    (r"403 Forbidden", "forbidden"),
    (r"Request blocked", "blocked"),
    (r"bot detection", "bot_detection"),
    (r"automated access", "bot_detection"),
    (r"Please verify you are a human", "captcha_generic"),
    (r"are you a robot", "captcha_generic"),
]

_COMPILED_PATTERNS = [(re.compile(p, re.IGNORECASE), btype) for p, btype in _BLOCK_PATTERNS]


def check_blocked(html: str, status_code: int = 200) -> BlockDetection:
    """Analyze HTML response for signs of bot detection or blocking.

    Args:
        html: The response body as a string.
        status_code: HTTP status code of the response.

    Returns:
        BlockDetection with is_blocked=True if blocking is detected.
    """
    # Status code checks
    if status_code == 403:
        return BlockDetection(
            is_blocked=True,
            block_type="http_403",
            details="Server returned 403 Forbidden",
        )
    if status_code == 429:
        return BlockDetection(
            is_blocked=True,
            block_type="rate_limited",
            details="Server returned 429 Too Many Requests",
        )
    if status_code == 503:
        # Could be Cloudflare challenge or legitimate downtime
        for pattern, block_type in _COMPILED_PATTERNS:
            if pattern.search(html):
                return BlockDetection(
                    is_blocked=True,
                    block_type=block_type,
                    details=f"503 with {block_type} pattern detected",
                )

    # Content pattern checks
    for pattern, block_type in _COMPILED_PATTERNS:
        if pattern.search(html):
            return BlockDetection(
                is_blocked=True,
                block_type=block_type,
                details=f"Pattern matched: {block_type}",
            )

    return BlockDetection(is_blocked=False)
