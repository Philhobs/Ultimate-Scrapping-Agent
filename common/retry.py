"""Tenacity-based async retry utilities."""

from __future__ import annotations

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

import httpx


def async_retry(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 10.0,
    retry_on: tuple[type[Exception], ...] = (httpx.TransportError, httpx.TimeoutException),
):
    """Return a tenacity retry decorator configured for async HTTP operations."""
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=min_wait, max=max_wait),
        retry=retry_if_exception_type(retry_on),
        reraise=True,
    )
