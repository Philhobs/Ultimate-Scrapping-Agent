"""Tier enum and TierManager state machine for scraping escalation."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class Tier(enum.IntEnum):
    """Scraping tiers, ordered by stealth level."""

    BASIC = 1       # Plain httpx GET
    STEALTH = 2     # httpx with headers/cookies
    BROWSER = 3     # Playwright headless
    PROXY = 4       # Proxy rotation


@dataclass
class TierManager:
    """State machine tracking the current scraping tier and escalation logic.

    Args:
        max_tier: Highest tier allowed (default 3, set to 4 to enable proxies).
        attempts_per_tier: How many retries before escalating.
    """

    max_tier: int = 3
    attempts_per_tier: int = 2
    current_tier: Tier = Tier.BASIC
    _attempt_counts: dict[Tier, int] = field(default_factory=lambda: {t: 0 for t in Tier})

    def record_attempt(self, tier: Tier | None = None) -> None:
        """Record an attempt at the given tier (defaults to current)."""
        tier = tier or self.current_tier
        self._attempt_counts[tier] = self._attempt_counts.get(tier, 0) + 1

    def should_escalate(self) -> bool:
        """Check if we've exhausted attempts at the current tier."""
        return self._attempt_counts.get(self.current_tier, 0) >= self.attempts_per_tier

    def escalate(self) -> Tier:
        """Move to the next tier. Returns the new tier.

        Raises:
            RuntimeError: If already at the maximum allowed tier.
        """
        if self.current_tier >= self.max_tier:
            raise RuntimeError(
                f"Cannot escalate beyond tier {self.current_tier} (max={self.max_tier})"
            )
        next_value = self.current_tier.value + 1
        self.current_tier = Tier(next_value)
        return self.current_tier

    def can_escalate(self) -> bool:
        """Check if escalation to a higher tier is possible."""
        return self.current_tier < self.max_tier

    def set_tier(self, tier: Tier) -> None:
        """Force a specific tier."""
        if tier.value > self.max_tier:
            raise ValueError(f"Tier {tier} exceeds max_tier={self.max_tier}")
        self.current_tier = tier

    def reset(self) -> None:
        """Reset to Tier 1 and clear attempt counts."""
        self.current_tier = Tier.BASIC
        self._attempt_counts = {t: 0 for t in Tier}

    def status(self) -> dict:
        """Return current tier status as a dict."""
        return {
            "current_tier": self.current_tier.value,
            "tier_name": self.current_tier.name,
            "max_tier": self.max_tier,
            "can_escalate": self.can_escalate(),
            "attempts": {t.name: self._attempt_counts.get(t, 0) for t in Tier},
        }
