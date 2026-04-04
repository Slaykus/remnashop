from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseSql
from .timestamp import TimestampMixin


class UserYandexQuota(BaseSql, TimestampMixin):
    __tablename__ = "user_yandex_quota"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.telegram_id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )

    is_restricted: Mapped[bool] = mapped_column(Boolean, default=False)
    period_start: Mapped[datetime]
    used_bytes: Mapped[int] = mapped_column(default=0)

    last_checked_at: Mapped[Optional[datetime]]
    warned_at: Mapped[Optional[datetime]]
    restricted_at: Mapped[Optional[datetime]]
