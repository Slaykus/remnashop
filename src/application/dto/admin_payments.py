"""
Страница платежей для админки кабинета.

Как и таблица клиентов, собирается одним запросом с пользователем: по
платежу админ сразу видит, чей он, а не ищет владельца отдельно.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

# «Не выданы» — FAILED: деньги списаны, а подписка не выдалась.
PaymentStatusTab = Literal["all", "completed", "failed", "pending", "canceled", "refunded"]


@dataclass(frozen=True)
class AdminPaymentsQuery:
    status: PaymentStatusTab = "all"
    gateway: Optional[str] = None
    purchase_type: Optional[str] = None
    # Поиск: id платежа, tg id или имя/ник клиента.
    q: str = ""
    payment_id: Optional[UUID] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    # Тестовые платежи по умолчанию прячем: это не деньги.
    include_test: bool = False
    page: int = 1
    per_page: int = 50


@dataclass(frozen=True)
class AdminPaymentRow:
    payment_id: UUID
    status: str
    purchase_type: str
    gateway_type: str
    currency: str
    original_amount: Optional[str]
    discount_percent: Optional[int]
    final_amount: Optional[str]
    plan_name: Optional[str]
    duration_days: Optional[int]
    extra_devices: int
    is_test: bool
    is_gift: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    telegram_id: Optional[int]
    user_name: str
    username: Optional[str]


@dataclass(frozen=True)
class AdminPaymentsPage:
    rows: list[AdminPaymentRow]
    total: int
    counts: dict[str, int] = field(default_factory=dict)
    # Сумма оплаченного в рублях при текущих фильтрах (кроме вкладки).
    paid_rub: Decimal = Decimal(0)
