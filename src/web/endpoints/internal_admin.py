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
from datetime import datetime, timedelta, timezone
from decimal import Decimal
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
from src.application.dto.admin_payments import AdminPaymentsQuery, PaymentStatusTab
from src.application.services.device_pricing import gifted_devices
from src.application.services.pricing import PricingService
from src.application.use_cases.gateways.commands.payment import ProcessPayment, ProcessPaymentDto
from src.application.use_cases.gateways.queries.providers import GetPaymentGatewayInstance
from src.application.use_cases.remnawave.commands.management import (
    AdminDeleteDevices,
    AdminDeleteDevicesDto,
)
from src.application.use_cases.subscription.commands.management import (
    UpdateDeviceLimit,
    UpdateDeviceLimitDto,
)
from src.application.use_cases.subscription.commands.set_plan import (
    SetUserSubscription,
    SetUserSubscriptionDto,
)
from src.core.constants import API_V1
from src.core.enums import PaymentGatewayType, TransactionStatus
from src.infrastructure.payment_gateways.yookassa import YookassaGateway

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


class AdminPlanOption(BaseModel):
    id: int
    name: str
    is_active: bool


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
    # Для смены тарифа в карточке; пробные не предлагаем.
    plans: list[AdminPlanOption]


def _plan_options(plans) -> list[AdminPlanOption]:  # type: ignore[no-untyped-def]
    return [
        AdminPlanOption(id=p.id or 0, name=p.name, is_active=p.is_active)
        for p in plans
        if not p.is_trial
    ]


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
    plan_dao: FromDishka[PlanDao],
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
        plans=_plan_options(await plan_dao.get_all()),
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
        plans=_plan_options(plans),
    )


# ---------------------------------------------------------------------------
# Действия
# ---------------------------------------------------------------------------
#
# Каждое действие проводится тем же сценарием, что и в админке бота (с
# синхронизацией панели), и возвращает состояние подписки до и после:
# кабинет пишет его в журнал действий, чтобы было видно, что поменялось.


class AdminSubscriptionState(BaseModel):
    plan_name: str | None
    device_limit: int | None
    extra_devices: int
    gifted_devices: int
    expire_at: datetime | None
    devices_connected: int | None = None


class AdminActionResult(BaseModel):
    before: AdminSubscriptionState
    after: AdminSubscriptionState


class AdminDeviceLimitRequest(BaseModel):
    device_limit: int
    # true — всё сверх тарифа платное (входит в цену продления);
    # false — сверх тарифа подарок, бесплатно и переживает продление.
    paid: bool = False


class AdminSetPlanRequest(BaseModel):
    plan_id: int
    # Сколько дней с сегодняшнего дня. Не указано — оставить текущий срок.
    days: int | None = None


class AdminDeleteDevicesRequest(BaseModel):
    # Не указано — удалить все.
    hwid: str | None = None


async def _client(user_dao: UserDao, telegram_id: int):  # type: ignore[no-untyped-def]
    user = await user_dao.get_by_telegram_id(telegram_id)
    if not user or not user.id:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    return user


async def _state(
    subscription_dao: SubscriptionDao, user_id: int, devices: int | None = None
) -> AdminSubscriptionState:
    sub = await subscription_dao.get_current(user_id)
    if not sub:
        return AdminSubscriptionState(
            plan_name=None, device_limit=None, extra_devices=0, gifted_devices=0, expire_at=None
        )
    return AdminSubscriptionState(
        plan_name=sub.plan_snapshot.name if sub.plan_snapshot else None,
        device_limit=sub.device_limit,
        extra_devices=sub.extra_devices,
        gifted_devices=gifted_devices(sub),
        expire_at=sub.expire_at,
        devices_connected=devices,
    )


def _refuse(e: Exception) -> HTTPException:
    logger.warning(f"Admin action refused: {e}")
    return HTTPException(status_code=400, detail=str(e)[:300])


@router.post("/users/{telegram_id}/device-limit", response_model=AdminActionResult)
@inject
async def set_device_limit(
    telegram_id: int,
    body: AdminDeviceLimitRequest,
    user_dao: FromDishka[UserDao],
    subscription_dao: FromDishka[SubscriptionDao],
    update_device_limit: FromDishka[UpdateDeviceLimit],
) -> AdminActionResult:
    if not (1 <= body.device_limit <= 100):
        raise HTTPException(status_code=400, detail="Лимит устройств — от 1 до 100")
    user = await _client(user_dao, telegram_id)
    before = await _state(subscription_dao, user.id)
    if before.device_limit is None:
        raise HTTPException(status_code=400, detail="У клиента нет подписки")
    try:
        await update_device_limit.system(
            UpdateDeviceLimitDto(user_id=user.id, device_limit=body.device_limit, paid=body.paid)
        )
    except ValueError as e:
        raise _refuse(e)
    return AdminActionResult(before=before, after=await _state(subscription_dao, user.id))


@router.post("/users/{telegram_id}/plan", response_model=AdminActionResult)
@inject
async def set_plan(
    telegram_id: int,
    body: AdminSetPlanRequest,
    user_dao: FromDishka[UserDao],
    subscription_dao: FromDishka[SubscriptionDao],
    set_subscription: FromDishka[SetUserSubscription],
) -> AdminActionResult:
    """
    Тариф без оплаты. Подписка пересоздаётся под тариф: докупленные и
    подаренные устройства сбрасываются до его лимита — кабинет говорит об
    этом до подтверждения. Срок — указанный или текущий.
    """
    user = await _client(user_dao, telegram_id)
    before = await _state(subscription_dao, user.id)
    if body.days is not None:
        days = body.days
    elif before.expire_at:
        days = _days_left(before.expire_at)
    else:
        days = 0
    if not (1 <= days <= 3650):
        raise HTTPException(status_code=400, detail="Срок — от 1 до 3650 дней")
    try:
        await set_subscription.system(
            SetUserSubscriptionDto(user_id=user.id, plan_id=body.plan_id, duration=days)
        )
    except ValueError as e:
        raise _refuse(e)
    return AdminActionResult(before=before, after=await _state(subscription_dao, user.id))


@router.post("/users/{telegram_id}/devices/delete", response_model=AdminActionResult)
@inject
async def delete_devices(
    telegram_id: int,
    body: AdminDeleteDevicesRequest,
    user_dao: FromDishka[UserDao],
    subscription_dao: FromDishka[SubscriptionDao],
    remnawave: FromDishka[Remnawave],
    admin_delete_devices: FromDishka[AdminDeleteDevices],
) -> AdminActionResult:
    user = await _client(user_dao, telegram_id)
    sub = await subscription_dao.get_current(user.id)
    if not sub:
        raise HTTPException(status_code=400, detail="У клиента нет подписки")
    connected = len(await remnawave.get_devices(sub.user_remna_id))
    before = await _state(subscription_dao, user.id, connected)
    try:
        await admin_delete_devices.system(AdminDeleteDevicesDto(user_id=user.id, hwid=body.hwid))
    except ValueError as e:
        raise _refuse(e)
    connected = len(await remnawave.get_devices(sub.user_remna_id))
    after = await _state(subscription_dao, user.id, connected)
    return AdminActionResult(before=before, after=after)


# ---------------------------------------------------------------------------
# Платежи
# ---------------------------------------------------------------------------


class AdminPaymentRowResponse(BaseModel):
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
    telegram_id: int | None
    user_name: str
    username: str | None


class AdminPaymentsResponse(BaseModel):
    rows: list[AdminPaymentRowResponse]
    total: int
    counts: dict[str, int]
    paid_rub: str
    page: int
    per_page: int


@router.get("/payments", response_model=AdminPaymentsResponse)
@inject
async def payments_page(
    transaction_dao: FromDishka[TransactionDao],
    status: PaymentStatusTab = "all",
    gateway: str | None = None,
    purchase_type: str | None = None,
    q: str = "",
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    include_test: bool = False,
    page: int = 1,
    per_page: int = 50,
) -> AdminPaymentsResponse:
    """Платежи с владельцами, фильтрами, счётчиками вкладок и суммой."""
    term = q.strip()
    try:
        payment_id = UUID(term) if term else None
    except ValueError:
        payment_id = None
    page, per_page = max(1, page), max(1, min(per_page, 100))
    result = await transaction_dao.admin_payments_page(
        AdminPaymentsQuery(
            status=status,
            gateway=gateway or None,
            purchase_type=purchase_type or None,
            q="" if payment_id else term,
            payment_id=payment_id,
            date_from=date_from,
            date_to=date_to,
            include_test=include_test,
            page=page,
            per_page=per_page,
        )
    )
    return AdminPaymentsResponse(
        rows=[
            AdminPaymentRowResponse(**{**asdict(r), "payment_id": str(r.payment_id)})
            for r in result.rows
        ],
        total=result.total,
        counts=result.counts,
        paid_rub=str(result.paid_rub),
        page=page,
        per_page=per_page,
    )


class AdminRetryResponse(BaseModel):
    payment_id: str
    telegram_id: int | None
    status_before: str
    status_after: str


@router.post("/payments/{payment_id}/retry", response_model=AdminRetryResponse)
@inject
async def retry_payment(
    payment_id: UUID,
    transaction_dao: FromDishka[TransactionDao],
    user_dao: FromDishka[UserDao],
    process_payment: FromDishka[ProcessPayment],
) -> AdminRetryResponse:
    """
    Повторить выдачу оплаченного, но не выданного платежа.

    То же проведение, что запускают вебхук ЮKassa и автоповтор, и безопасно
    по той же причине: переход FAILED -> COMPLETED атомарен, партнёрская
    доля защищена уникальным ключом. Нужно, когда автоповтор уже отступился
    (его окно — несколько часов) или ждать нельзя.
    """
    transaction = await transaction_dao.get_by_payment_id(payment_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Платёж не найден")
    if (
        transaction.status != TransactionStatus.FAILED
        or transaction.is_test
        or transaction.is_gift
    ):
        raise HTTPException(
            status_code=400,
            detail="Повторить можно только оплаченный, но не выданный платёж",
        )
    user = await user_dao.get_by_id(transaction.user_id)
    try:
        await process_payment.system(
            ProcessPaymentDto(
                payment_id=payment_id,
                new_transaction_status=TransactionStatus.COMPLETED,
                gateway_type=transaction.gateway_type,
            )
        )
    except Exception as e:
        logger.warning(f"Admin retry of payment {payment_id} failed: {e!r}")
        raise HTTPException(status_code=400, detail=f"Выдать снова не удалось: {str(e)[:200]}")
    after = await transaction_dao.get_by_payment_id(payment_id)
    return AdminRetryResponse(
        payment_id=str(payment_id),
        telegram_id=user.telegram_id if user else None,
        status_before=_enum_value(transaction.status),
        status_after=_enum_value(after.status) if after else "",
    )


class ReconcileItem(BaseModel):
    payment_id: str
    created_at: str | None
    amount: str | None
    description: str
    # Что у нас: статус и сумма; у «нет записи» пусто.
    our_status: str | None = None
    our_amount: str | None = None
    telegram_id: int | None = None


class ReconcileResponse(BaseModel):
    since: datetime
    yookassa_succeeded: int
    test_skipped: int
    # Деньги пришли, а записи у нас нет.
    missing: list[ReconcileItem]
    # Деньги пришли, а у нас платёж не оплачен (ожидает, отменён, не выдан).
    not_completed: list[ReconcileItem]
    # Оплачен у обоих, но суммы разные.
    amount_mismatch: list[ReconcileItem]


@router.get("/payments/reconcile", response_model=ReconcileResponse)
@inject
async def reconcile_yookassa(
    transaction_dao: FromDishka[TransactionDao],
    user_dao: FromDishka[UserDao],
    get_gateway: FromDishka[GetPaymentGatewayInstance],
    days: int = 30,
) -> ReconcileResponse:
    """
    Сверка успешных платежей ЮKassa с базой бота — то, что раньше делал
    скрипт reconcile_yookassa.py. Только читает: и ЮKassa, и базу.
    """
    days = max(1, min(days, 180))
    since = datetime.now(timezone.utc) - timedelta(days=days)
    try:
        gateway = await get_gateway.system(PaymentGatewayType.YOOKASSA)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"ЮKassa не настроена: {e}")
    if not isinstance(gateway, YookassaGateway):
        raise HTTPException(status_code=400, detail="ЮKassa не настроена")
    try:
        payments = await gateway.list_succeeded_since(since)
    except Exception as e:
        logger.warning(f"YooKassa reconcile failed: {e!r}")
        raise HTTPException(status_code=502, detail="ЮKassa не ответила")

    return await _reconcile(payments, since, transaction_dao, user_dao)


async def _reconcile(
    payments: list[dict],
    since: datetime,
    transaction_dao: TransactionDao,
    user_dao: UserDao,
) -> ReconcileResponse:
    real = [p for p in payments if not p["test"]]
    ids = []
    for p in real:
        try:
            ids.append(UUID(p["id"]))
        except ValueError:
            continue
    ours = {str(t.payment_id): t for t in await transaction_dao.get_by_payment_ids(ids)}

    owners: dict[int, int | None] = {}

    async def owner(user_id: int) -> int | None:
        if user_id not in owners:
            u = await user_dao.get_by_id(user_id)
            owners[user_id] = u.telegram_id if u else None
        return owners[user_id]

    missing, not_completed, mismatch = [], [], []
    for p in sorted(real, key=lambda x: x.get("created_at") or ""):
        item = ReconcileItem(
            payment_id=p["id"],
            created_at=p.get("created_at"),
            amount=p.get("amount"),
            description=p.get("description") or "",
        )
        t = ours.get(p["id"])
        if t is None:
            missing.append(item)
            continue
        item.our_status = _enum_value(t.status)
        item.our_amount = str(t.pricing.final_amount) if t.pricing else None
        item.telegram_id = await owner(t.user_id)
        if t.status not in (TransactionStatus.COMPLETED, TransactionStatus.REFUNDED):
            not_completed.append(item)
        elif (
            t.pricing
            and p.get("amount") is not None
            and Decimal(str(p["amount"])) != Decimal(str(t.pricing.final_amount))
        ):
            mismatch.append(item)

    return ReconcileResponse(
        since=since,
        yookassa_succeeded=len(real),
        test_skipped=len(payments) - len(real),
        missing=missing,
        not_completed=not_completed,
        amount_mismatch=mismatch,
    )
