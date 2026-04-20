from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from .base import BaseDto


@dataclass(kw_only=True)
class UserYandexQuotaDto(BaseDto):
    user_telegram_id: int
    is_restricted: bool = False
    period_start: datetime
    used_bytes: int = 0
    reset_baseline_bytes: int = 0
    last_checked_at: Optional[datetime] = None
    warned_at: Optional[datetime] = None
    restricted_at: Optional[datetime] = None
    # TimestampMixin fields (optional for conversion)
    created_at: Optional[datetime] = field(default=None)
    updated_at: Optional[datetime] = field(default=None)
