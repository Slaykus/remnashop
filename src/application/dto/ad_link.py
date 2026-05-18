from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional

from .base import BaseDto


@dataclass(kw_only=True)
class AdLinkDto(BaseDto):
    id: int
    code: str
    name: str
    is_active: bool = True
    bonus_points: int = 0
    bonus_days: int = 0
    bonus_discount_pct: int = 0
    clicks_count: int = 0
    created_at: Optional[datetime] = field(default=None)
    updated_at: Optional[datetime] = field(default=None)


@dataclass(kw_only=True)
class AdLinkUserDto(BaseDto):
    id: int
    ad_link_id: int
    user_telegram_id: int
    bonus_issued: bool = False
    created_at: Optional[datetime] = field(default=None)


@dataclass
class AdLinkStatsDto:
    unique_clicks: int = 0
    bonus_issued_count: int = 0
    trial_count: int = 0
    paid_count: int = 0
    revenue_rub: Decimal = field(default_factory=lambda: Decimal("0"))
