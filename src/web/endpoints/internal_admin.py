"""
Админка кабинета: таблица клиентов и карточка клиента.

Только чтение. Админка ничего не пишет в базу бота и в панель напрямую:
действия появятся отдельными ручками и пойдут теми же сценариями, что и в
боте. Здесь — то, что нужно, чтобы разобраться с клиентом за минуту, а не
собирать картину из базы, панели и логов.

Наружу не уходят ссылка подписки (по ней можно подключиться от имени
клиента) и IP устройств: для разбора они не нужны.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Annotated
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from pydantic import BaseModel
from remnapy import RemnawaveSDK

from src.application.common import Remnawave
from src.application.common.dao import (
    PartnerDao,
    PlanDao,
    ReferralDao,
    SubscriptionDao,
    TransactionDao,
    UserDao,
)
from src.application.dto.admin_clients import (
    AdminClientsQuery,
    ClientSort,
    ClientSource,
    ClientStatusFilter,
)
from src.application.services.device_pricing import gifted_devices
from src.application.services.pricing import PricingService
from src.core.constants import API_V1

from .internal import _days_left, _enum_value, verify_internal_key

router = APIRouter(
    prefix=API_V1 + "/internal/admin",
    tags=["internal-admin"],
    dependencies=[Depends(verify_internal_key)],
)

TRANSACTIONS_LIMIT = 50


# ---------------------------------------------------------------------------
# Карточка
# ---------------------------------------------------------------------------


class AdminCardUser(BaseModel):
    id: int
    telegram_id: int
    name: str
    username: str | None
    created_at: datetime | None
    is_blocked: bool
    is_bot_blocked: bool
    is_trial_available: bool
    personal_discount: int
    purchase_discount: int
    ad_link_id: int | None


class AdminCardSubscription(BaseModel):
    id: int
    status: str
    is_trial: bool
    plan_id: int | None
    plan_name: str
    # Лимит устройств по частям: тариф + докуплено (входит в цену продления)
    # + подарено вручную (бесплатно). Ноль в лимите — безлимит.
    device_limit: int
    plan_devices: int
    extra_devices: int
    gifted_devices: int
    traffic_limit_gb: int
    traffic_strategy: str
    expire_at: datetime
    days_left: int
    remna_uuid: str
    created_at: datetime | None


class AdminCardPanel(BaseModel):
    status: str | None = None
    used_traffic_bytes: float | None = None
    online_at: datetime | None = None
    # Панель не ответила — карточка всё равно показывается, без этих данных.
    error: str | None = None


class AdminCardDevice(BaseModel):
    hwid: str
    platform: str | None
    os_version: str | None
    device_model: str | None
    created_at: datetime
    updated_at: datetime


class AdminCardTransaction(BaseModel):
    payment_id: str
    status: str
    purchase_type: str
    gateway_type: str
    currency: str
    original_amount: str | None
    discount_percent: int | None
    final_amount: str | None
    plan_name: str | None
    duration_days: int | None
    extra_devices: int
    is_test: bool
    is_gift: bool
    created_at: datetime | None
    updated_at: datetime | None


class AdminCardPerson(BaseModel):
    telegram_id: int
    name: str
    username: str | None


class AdminCardResponse(BaseModel):
    user: AdminCardUser
    subscription: AdminCardSubscription | None
    panel: AdminCardPanel | None
    devices: list[AdminCardDevice] | None
    devices_error: str | None
    transactions: list[AdminCardTransaction]
    transactions_total: int
    referrer: AdminCardPerson | None
    invited_count: int
    is_partner: bool


def _short_error(e: Exception) -> str:
    return f"{type(e).__name__}: {e}"[:200]


@router.get("/users/{telegram_id}/card", response_model=AdminCardResponse)
@inject
async def client_card(
    telegram_id: int,
    user_dao: FromDishka[UserDao],
    subscription_dao: FromDishka[SubscriptionDao],
    transaction_dao: FromDishka[TransactionDao],
    referral_dao: FromDishka[ReferralDao],
    partner_dao: FromDishka[PartnerDao],
    remnawave: FromDishka[Remnawave],
    sdk: FromDishka[RemnawaveSDK],
) -> AdminCardResponse:
    """
    Всё о клиенте одним ответом: профиль, подписка с разбивкой устройств,
    данные панели, устройства, платежи, кто пригласил.

    Панель опрашивается дважды (пользователь и устройства). Её ошибка не
    роняет карточку: база бота важнее, и разбирать клиента нужно как раз
    тогда, когда что-то идёт не так.
    """
    user = await user_dao.get_by_telegram_id(telegram_id)
    if not user or not user.id:
        raise HTTPException(status_code=404, detail="User not found")

    subscription = await subscription_dao.get_current(user.id)

    sub_out = None
    panel = None
    devices = None
    devices_error = None
    if subscription:
        snapshot = subscription.plan_snapshot
        sub_out = AdminCardSubscription(
            id=subscription.id or 0,
            status=_enum_value(subscription.current_status),
            is_trial=subscription.is_trial,
            plan_id=snapshot.id if snapshot else None,
            plan_name=snapshot.name if snapshot else "",
            device_limit=subscription.device_limit,
            plan_devices=snapshot.device_limit if snapshot else 0,
            extra_devices=subscription.extra_devices,
            gifted_devices=gifted_devices(subscription),
            traffic_limit_gb=subscription.traffic_limit,
            traffic_strategy=_enum_value(subscription.traffic_limit_strategy),
            expire_at=subscription.expire_at,
            days_left=_days_left(subscription.expire_at),
            remna_uuid=str(subscription.user_remna_id),
            created_at=subscription.created_at,
        )

        try:
            remna_user = await sdk.users.get_user_by_uuid(uuid=str(subscription.user_remna_id))
            panel = AdminCardPanel(
                status=_enum_value(getattr(remna_user, "status", "")) or None,
                used_traffic_bytes=getattr(remna_user, "used_traffic_bytes", None),
                online_at=getattr(remna_user, "online_at", None),
            )
        except Exception as e:
            logger.warning(f"Admin card: panel user for '{telegram_id}' failed: {e}")
            panel = AdminCardPanel(error=_short_error(e))

        try:
            devices = [
                AdminCardDevice(
                    hwid=d.hwid,
                    platform=d.platform,
                    os_version=d.os_version,
                    device_model=d.device_model,
                    created_at=d.created_at,
                    updated_at=d.updated_at,
                )
                for d in await remnawave.get_devices(subscription.user_remna_id)
            ]
        except Exception as e:
            logger.warning(f"Admin card: devices for '{telegram_id}' failed: {e}")
            devices_error = _short_error(e)

    transactions = await transaction_dao.get_by_user(user.id)
    tx_out = []
    for t in transactions[:TRANSACTIONS_LIMIT]:
        pricing = t.pricing
        snapshot = t.plan_snapshot
        tx_out.append(
            AdminCardTransaction(
                payment_id=str(t.payment_id),
                status=_enum_value(t.status),
                purchase_type=_enum_value(t.purchase_type),
                gateway_type=_enum_value(t.gateway_type),
                currency=_enum_value(t.currency),
                original_amount=str(pricing.original_amount) if pricing else None,
                discount_percent=pricing.discount_percent if pricing else None,
                final_amount=str(pricing.final_amount) if pricing else None,
                plan_name=snapshot.name if snapshot else None,
                duration_days=snapshot.duration if snapshot else None,
                extra_devices=getattr(snapshot, "extra_devices", 0) if snapshot else 0,
                is_test=t.is_test,
                is_gift=t.is_gift,
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
        )

    referral = await referral_dao.get_by_referred_id(user.id)
    referrer = None
    if referral and referral.referrer:
        referrer = AdminCardPerson(
            telegram_id=referral.referrer.telegram_id,
            name=referral.referrer.name or "",
            username=referral.referrer.username,
        )

    return AdminCardResponse(
        user=AdminCardUser(
            id=user.id,
            telegram_id=user.telegram_id,
            name=user.name or "",
            username=user.username,
            created_at=user.created_at,
            is_blocked=user.is_blocked,
            is_bot_blocked=user.is_bot_blocked,
            is_trial_available=user.is_trial_available,
            personal_discount=user.personal_discount or 0,
            purchase_discount=PricingService.get_live_purchase_discount(user),
            ad_link_id=user.ad_link_id,
        ),
        subscription=sub_out,
        panel=panel,
        devices=devices,
        devices_error=devices_error,
        transactions=tx_out,
        transactions_total=len(transactions),
        referrer=referrer,
        invited_count=await referral_dao.get_referrals_count(user.id),
        is_partner=await partner_dao.get_by_user_id(user.id) is not None,
    )


# ---------------------------------------------------------------------------
# Таблица клиентов
# ---------------------------------------------------------------------------


class AdminClientRowResponse(BaseModel):
    user_id: int
    telegram_id: int
    name: str
    username: str | None
    created_at: datetime | None
    is_blocked: bool
    is_bot_blocked: bool
    personal_discount: int
    subscription_status: str | None
    is_trial: bool
    plan_id: int | None
    plan_name: str | None
    expire_at: datetime | None
    device_limit: int | None
    paid_rub: str
    payments: int


class AdminPlanOption(BaseModel):
    id: int
    name: str
    is_active: bool


class AdminClientsResponse(BaseModel):
    rows: list[AdminClientRowResponse]
    total: int
    counts: dict[str, int]
    page: int
    per_page: int
    plans: list[AdminPlanOption]


@router.get("/clients", response_model=AdminClientsResponse)
@inject
async def clients_page(
    user_dao: FromDishka[UserDao],
    plan_dao: FromDishka[PlanDao],
    status: ClientStatusFilter = "all",
    source: ClientSource = "all",
    plan_id: int | None = None,
    sort: ClientSort = "created",
    q: str = "",
    extra_telegram_ids: Annotated[list[int] | None, Query()] = None,
    page: int = 1,
    per_page: int = 25,
) -> AdminClientsResponse:
    """
    Все клиенты бота — и из телеграма, и с сайта — постранично, с
    фильтрами и счётчиками вкладок. Один запрос в базу на страницу.

    `extra_telegram_ids` — клиенты, найденные кабинетом по логину на
    сайте: бот логинов не знает, а показать их нужно в той же таблице.
    """
    term = q.strip()
    try:
        payment_id = UUID(term) if term else None
    except ValueError:
        payment_id = None

    result = await user_dao.admin_clients_page(
        AdminClientsQuery(
            status=status,
            source=source,
            plan_id=plan_id,
            sort=sort,
            q="" if payment_id else term,
            payment_id=payment_id,
            extra_telegram_ids=tuple(extra_telegram_ids or ()),
            page=max(1, page),
            per_page=max(1, min(per_page, 100)),
        )
    )
    plans = await plan_dao.get_all()
    return AdminClientsResponse(
        rows=[
            AdminClientRowResponse(**{**asdict(r), "paid_rub": str(r.paid_rub)})
            for r in result.rows
        ],
        total=result.total,
        counts=result.counts,
        page=max(1, page),
        per_page=max(1, min(per_page, 100)),
        plans=[
            AdminPlanOption(id=p.id or 0, name=p.name, is_active=p.is_active)
            for p in plans
            if not p.is_trial
        ],
    )
