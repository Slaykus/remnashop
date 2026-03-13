from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.core.enums import ReferralLevel, ReferralRewardType

from .base import BaseDto, TimestampMixin, TrackableMixin
from .user import UserDto


@dataclass
class ReferralStatisticsDto:
    total_referrals: int
    level_1_count: int
    level_2_count: int
    unique_referrers: int
    total_rewards_issued: int
    total_rewards_pending: int
    total_points_issued: int
    total_days_issued: int
    total_points_pending: int
    total_days_pending: int
    top_referrer_invited_count: int
    top_referrer_username: Optional[str] = None
    top_referrer_telegram_id: Optional[int] = None


@dataclass(kw_only=True)
class ReferralDto(BaseDto, TrackableMixin, TimestampMixin):
    level: ReferralLevel

    referrer: "UserDto"
    referred: "UserDto"


@dataclass(kw_only=True)
class ReferralRewardDto(BaseDto, TrackableMixin, TimestampMixin):
    user_telegram_id: int

    type: ReferralRewardType
    amount: int
    is_issued: bool = False

    @property
    def rewarded_at(self) -> Optional[datetime]:
        return self.created_at
