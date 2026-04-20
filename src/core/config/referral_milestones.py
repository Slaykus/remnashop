from .base import BaseConfig


# Milestone tier definitions (referrals_needed -> discount_percent, prefix_emoji, prefix_name)
MILESTONE_TIERS: list[tuple[int, int, str, str]] = [
    (10, 25, "🌧️", "Дождь"),
    (5, 15, "⛈️", "Шторм"),
    (3, 10, "☁️", "Облако"),
    (1, 5, "💧", "Капля"),
]


def get_tier_for_count(count: int) -> int:
    """Return tier index (0 = no tier, 1..4 = tier level) for given paid referrals count."""
    if count >= 10:
        return 4
    if count >= 5:
        return 3
    if count >= 3:
        return 2
    if count >= 1:
        return 1
    return 0


def get_discount_for_tier(tier: int) -> int:
    """Return discount percent for a given tier (0 = no discount)."""
    discounts = [0, 5, 10, 15, 25]
    return discounts[tier] if 0 <= tier < len(discounts) else 0


class ReferralMilestonesConfig(BaseConfig, env_prefix="REFERRAL_MILESTONE_"):
    enabled: bool = True
