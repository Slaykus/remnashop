from datetime import datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseSql
from .timestamp import TimestampMixin


class AdLink(BaseSql, TimestampMixin):
    __tablename__ = "ad_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    bonus_points: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    bonus_days: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    bonus_discount_pct: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    clicks_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class AdLinkUser(BaseSql):
    __tablename__ = "ad_link_users"
    __table_args__ = (
        UniqueConstraint("ad_link_id", "user_telegram_id", name="uq_ad_link_users"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    ad_link_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ad_links.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_telegram_id: Mapped[int] = mapped_column(BigInteger, index=True, nullable=False)
    bonus_issued: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime]
