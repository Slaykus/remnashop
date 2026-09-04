from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from src.core.enums import MediaType, TextFormat

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
    # Разовая: уходит в purchase_discount и сгорает после первой оплаты.
    bonus_discount_once_pct: int = 0
    clicks_count: int = 0
    # Владелец ссылки: пусто — своя реклама, заполнено — партнёрская.
    owner_user_id: Optional[int] = field(default=None)
    promo_text: Optional[str] = field(default=None)
    # file_id вложения и его тип. Имя поля осталось от времён, когда промо
    # умело только фото; переименовывать не стали, чтобы не тащить миграцию
    # ради косметики. Пусто в типе — фото, так читаются старые записи.
    promo_photo_id: Optional[str] = field(default=None)
    promo_media_type: Optional[MediaType] = field(default=None)
    # Пусто — разметка телеграма, как было всегда; MARKDOWN — rich-пост.
    promo_format: Optional[TextFormat] = field(default=None)
    promo_buttons: list[Any] = field(default_factory=list)
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


@dataclass
class AdLinkDailyClickDto:
    day: date
    unique_clicks: int


@dataclass
class AdLinkComparisonItemDto:
    id: int
    name: str
    code: str
    is_active: bool
    clicks_count: int
    unique_clicks: int
    paid_count: int
    revenue_rub: Decimal
    conversion_pct: float = 0.0
