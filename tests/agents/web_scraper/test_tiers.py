"""Tests for TierManager escalation logic."""

from __future__ import annotations

import pytest

from agents.web_scraper.scraping.tiers import Tier, TierManager


class TestTierManager:
    def test_starts_at_basic(self, tier_manager: TierManager):
        assert tier_manager.current_tier == Tier.BASIC

    def test_escalate_basic_to_stealth(self, tier_manager: TierManager):
        new_tier = tier_manager.escalate()
        assert new_tier == Tier.STEALTH
        assert tier_manager.current_tier == Tier.STEALTH

    def test_escalate_through_all_tiers(self):
        tm = TierManager(max_tier=4)
        assert tm.escalate() == Tier.STEALTH
        assert tm.escalate() == Tier.BROWSER
        assert tm.escalate() == Tier.PROXY

    def test_cannot_escalate_beyond_max(self, tier_manager: TierManager):
        tier_manager.escalate()  # -> STEALTH
        tier_manager.escalate()  # -> BROWSER
        with pytest.raises(RuntimeError, match="Cannot escalate beyond"):
            tier_manager.escalate()

    def test_should_escalate_after_attempts(self, tier_manager: TierManager):
        assert not tier_manager.should_escalate()
        tier_manager.record_attempt()
        assert not tier_manager.should_escalate()
        tier_manager.record_attempt()
        assert tier_manager.should_escalate()

    def test_can_escalate(self, tier_manager: TierManager):
        assert tier_manager.can_escalate()
        tier_manager.set_tier(Tier.BROWSER)
        assert not tier_manager.can_escalate()  # max_tier=3

    def test_set_tier(self, tier_manager: TierManager):
        tier_manager.set_tier(Tier.BROWSER)
        assert tier_manager.current_tier == Tier.BROWSER

    def test_set_tier_exceeds_max(self, tier_manager: TierManager):
        with pytest.raises(ValueError, match="exceeds max_tier"):
            tier_manager.set_tier(Tier.PROXY)

    def test_reset(self, tier_manager: TierManager):
        tier_manager.escalate()
        tier_manager.record_attempt()
        tier_manager.record_attempt()
        tier_manager.reset()
        assert tier_manager.current_tier == Tier.BASIC
        assert not tier_manager.should_escalate()

    def test_status(self, tier_manager: TierManager):
        status = tier_manager.status()
        assert status["current_tier"] == 1
        assert status["tier_name"] == "BASIC"
        assert status["max_tier"] == 3
        assert status["can_escalate"] is True

    def test_record_attempt_specific_tier(self, tier_manager: TierManager):
        tier_manager.record_attempt(Tier.STEALTH)
        # Current tier attempts should be unaffected
        assert not tier_manager.should_escalate()

    def test_escalation_flow(self):
        """Simulate a real escalation scenario."""
        tm = TierManager(max_tier=3, attempts_per_tier=2)

        # Try basic twice, should escalate
        tm.record_attempt()
        tm.record_attempt()
        assert tm.should_escalate()
        assert tm.can_escalate()
        tm.escalate()
        assert tm.current_tier == Tier.STEALTH

        # Try stealth twice, should escalate
        tm.record_attempt()
        tm.record_attempt()
        assert tm.should_escalate()
        assert tm.can_escalate()
        tm.escalate()
        assert tm.current_tier == Tier.BROWSER

        # At max tier, can't escalate
        tm.record_attempt()
        tm.record_attempt()
        assert tm.should_escalate()
        assert not tm.can_escalate()
