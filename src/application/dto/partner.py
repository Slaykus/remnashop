from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional

from .base import BaseDto


@dataclass(kw_only=True)
class PartnerDto(BaseDto):
    id: int
    user_id: int
    rate_pct: Decimal
    hold_days: int
    min_payout: Decimal
    is_active: bool = True
    payout_details: Optional[str] = field(default=None)
    note: Optional[str] = field(default=None)
    created_at: Optional[datetime] = field(default=None)
    payout_requested_at: Optional[datetime] = field(default=None)


@dataclass(kw_only=True)
class PartnerEarningDto(BaseDto):
    id: int
    partner_id: int
    transaction_id: int
    referred_user_id: Optional[int]
    amount: Decimal
    # Ставка на момент начисления, а не текущая ставка партнёра.
    rate_pct: Decimal
    payment_amount: Decimal
    status: str
    available_at: datetime
    created_at: datetime
    paid_at: Optional[datetime] = field(default=None)


@dataclass(kw_only=True)
class PartnerBalanceDto(BaseDto):
    """Сколько партнёру начислено, сколько уже можно платить и сколько отдано."""

    # Ждёт окончания периода удержания.
    pending: Decimal
    # Срок вышел, выплата не оформлена.
    available: Decimal
    # Уже выплачено.
    paid: Decimal
    # Всего начислено за всё время, включая выплаченное.
    total: Decimal
    # Сколько платежей учтено.
    payments_count: int


@dataclass(kw_only=True)
class PartnerPayoutDto(BaseDto):
    id: int
    partner_id: int
    amount: Decimal
    note: Optional[str] = field(default=None)
    created_at: datetime
    created_by: Optional[int] = field(default=None)
    # Сколько начислений закрыто этой выплатой.
    earnings_count: int = 0
