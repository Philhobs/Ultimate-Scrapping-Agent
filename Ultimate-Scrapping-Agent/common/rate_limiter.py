"""Async token-bucket rate limiter."""

from __future__ import annotations

import asyncio
import time


class RateLimiter:
    """Token-bucket rate limiter for async operations.

    Args:
        rate: Tokens added per second.
        burst: Maximum token capacity.
    """

    def __init__(self, rate: float = 5.0, burst: int = 10) -> None:
        self.rate = rate
        self.burst = burst
        self._tokens = float(burst)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
        self._last_refill = now

    async def acquire(self) -> None:
        """Wait until a token is available, then consume it."""
        async with self._lock:
            self._refill()
            while self._tokens < 1:
                wait_time = (1 - self._tokens) / self.rate
                await asyncio.sleep(wait_time)
                self._refill()
            self._tokens -= 1
