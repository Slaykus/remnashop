"""
Страница таблицы клиентов для админки кабинета.

Вынесено в отдельные dto, а не собирается из UserDto и SubscriptionDto:
таблице нужны поля из трёх таблиц сразу (пользователь, текущая подписка,
сумма оплат), и собирать их по одному клиенту — сотни запросов на страницу.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Literal, Optional
from uuid import UUID

# Вкладки таблицы. «Истекает» — активные, у которых осталось не больше
# недели: это те, кому пора напомнить.
ClientStatusFilter = Literal["all", "active", "expiring", "trial", "expired", "limited", "none"]
ClientSource = Literal["all", "telegram", "site"]
ClientSort = Literal["created", "expire", "paid", "name"]


@dataclass(frozen=True)
class AdminClientsQuery:
    status: ClientStatusFilter = "all"
    source: ClientSource = "all"
    plan_id: Optional[int] = None
    sort: ClientSort = "created"
    # Поиск: имя или ник, tg id или id в боте, id платежа.
    q: str = ""
    # Найденные кабинетом по логину на сайте — бот логинов не знает.
    extra_telegram_ids: tuple[int, ...] = ()
    payment_id: Optional[UUID] = None
    page: int = 1
    per_page: int = 25


@dataclass(frozen=True)
class AdminClientRow:
    user_id: int
    telegram_id: int
    name: str
    username: Optional[str]
    created_at: Optional[datetime]
    is_blocked: bool
    is_bot_blocked: bool
    personal_discount: int
    subscription_status: Optional[str]
    is_trial: bool
    plan_id: Optional[int]
    plan_name: Optional[str]
    expire_at: Optional[datetime]
    device_limit: Optional[int]
    paid_rub: Decimal
    payments: int


@dataclass(frozen=True)
class AdminClientsPage:
    rows: list[AdminClientRow]
    total: int
    # Сколько клиентов в каждой вкладке — при текущих источнике, тарифе и
    # поиске, чтобы цифры на вкладках совпадали с тем, что откроется.
    counts: dict[str, int] = field(default_factory=dict)
