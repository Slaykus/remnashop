"""
Internal API for Rain VPN Web Personal Cabinet.

Endpoints protected by X-Internal-Key header (APP_WEB_API_KEY env var).
"""

from __future__ import annotations

import hashlib
import math
import os
import secrets
from datetime import datetime, timezone
from uuid import UUID
from typing import Annotated

from loguru import logger

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from remnapy import RemnawaveSDK

from src.application.common import BotService, Remnawave
from decimal import Decimal

from src.core.enums import ReferralLevel
from src.application.common.dao import AdLinkDao, PartnerDao, PlanDao, PaymentGatewayDao, PromocodeDao, ReferralDao, SubscriptionDao, TransactionDao, UserDao, NodeQuotaDao
from src.core.config import AppConfig
from src.application.common.uow import UnitOfWork
from src.application.dto import ReferralDto, UserDto
from src.application.use_cases.partner.commands.manage import (
    CreatePartnerLink,
    CreatePartnerLinkDto,
)
from src.application.dto.plan import PlanSnapshotDto
from src.application.dto.transaction import PriceDetailsDto
from src.application.use_cases.gateways.commands.payment import CreatePayment, CreatePaymentDto
from src.application.use_cases.remnawave.commands.management import DeleteUserDeviceDto, DeleteUserDevice, ReissueSubscription
from src.application.use_cases.user.queries.plans import GetAvailablePlans, GetAvailableTrial
from src.application.use_cases.subscription import AddSubscriptionDuration
from src.application.use_cases.subscription.commands.management import AddSubscriptionDurationDto
from src.application.use_cases.subscription.commands.purchase import ActivateFreePlan, ActivateFreePlanDto
from src.application.use_cases.gateways.commands.payment import gift_code_for_payment
from src.application.use_cases.promocode.commands.activate import ActivatePromocode, ActivatePromocodeDto
from src.application.use_cases.user import SetUserPersonalDiscount
from src.application.use_cases.user.commands.profile_edit import SetUserPersonalDiscountDto
from src.core.exceptions import (
    PromocodeAlreadyActivatedError,
    PromocodeError,
    PromocodeExpiredError,
    PromocodeNotAvailableError,
    PromocodeNotFoundError,
)
from src.core.enums import PaymentGatewayType, PlanAvailability, PurchaseType, ReferralRewardType, TransactionStatus
from src.core.constants import API_V1

router = APIRouter(prefix=API_V1 + "/internal", tags=["internal"])

_ENV_KEY = "APP_WEB_API_KEY"


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


async def verify_internal_key(x_internal_key: Annotated[str, Header()]) -> None:
    expected = os.environ.get(_ENV_KEY, "")
    if not expected:
        raise HTTPException(status_code=503, detail="Internal API is not configured (APP_WEB_API_KEY not set)")
    if not secrets.compare_digest(x_internal_key.encode(), expected.encode()):
        raise HTTPException(status_code=403, detail="Forbidden")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class UserResponse(BaseModel):
    id: int
    telegram_id: int
    username: str
    name: str
    points: int
    is_blocked: bool
    created_at: datetime
    personal_discount: int
    purchase_discount: int


class SubscriptionResponse(BaseModel):
    id: int
    status: str
    is_trial: bool
    expire_at: datetime | None
    days_left: int
    traffic_limit: int
    device_limit: int
    url: str | None
    plan_tag: str | None
    used_traffic_bytes: int = 0


class PlanPriceResponse(BaseModel):
    currency: str
    price: str


class PlanDurationResponse(BaseModel):
    id: int
    days: int
    prices: list[PlanPriceResponse]


class PlanResponse(BaseModel):
    id: int
    name: str
    type: str
    traffic_limit: int
    device_limit: int
    availability: str
    # Имя поля в ответе оставлено прежним ради совместимости с кабинетом;
    # в PlanDto оно с версии 0.8 называется allowed_telegram_ids.
    allowed_user_ids: list[int]
    durations: list[PlanDurationResponse]


class DeviceResponse(BaseModel):
    hwid: str
    platform: str | None
    device_model: str | None


class TransactionResponse(BaseModel):
    payment_id: str
    status: str
    purchase_type: str
    gateway_type: str
    currency: str
    amount: str | None
    created_at: datetime


class NodeResponse(BaseModel):
    uuid: str
    name: str
    address: str
    is_disabled: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _days_left(expire_at: datetime | None) -> int:
    """
    Остаток в днях, округлённый вверх.

    Округление вниз давало ноль у любой подписки, которой осталось меньше
    суток: свежий суточный пробный период показывался как «0 дней» сразу
    после выдачи. Неполный день человек считает днём, поэтому вверх.
    """
    if expire_at is None:
        return 0
    now = datetime.now(timezone.utc)
    if expire_at.tzinfo is None:
        expire_at = expire_at.replace(tzinfo=timezone.utc)
    seconds = (expire_at - now).total_seconds()
    if seconds <= 0:
        return 0
    return math.ceil(seconds / 86400)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/users/{telegram_id}",
    response_model=UserResponse,
    dependencies=[Depends(verify_internal_key)],
)
@inject
async def get_user(
    telegram_id: int,
    user_dao: FromDishka[UserDao],
) -> UserResponse:
    user = await user_dao.get_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(
        id=user.id or 0,
        telegram_id=user.telegram_id,
        username=user.username or "",
        name=user.name or "",
        points=getattr(user, "points", 0),
        is_blocked=getattr(user, "is_blocked", False),
        created_at=user.created_at or datetime.now(timezone.utc),
        personal_discount=getattr(user, "personal_discount", 0),
        purchase_discount=getattr(user, "purchase_discount", 0),
    )


@router.get(
    "/subscriptions/{telegram_id}",
    response_model=SubscriptionResponse,
    dependencies=[Depends(verify_internal_key)],
)
@inject
async def get_subscription(
    telegram_id: int,
    subscription_dao: FromDishka[SubscriptionDao],
    sdk: FromDishka[RemnawaveSDK],
) -> SubscriptionResponse:
    sub = await subscription_dao.get_current_by_telegram_id(telegram_id)
    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription found")

    used_bytes = 0
    if sub.user_remna_id:
        try:
            remna_user = await sdk.users.get_user_by_uuid(uuid=str(sub.user_remna_id))
            used_bytes = getattr(remna_user, "used_traffic_bytes", 0) or 0
        except Exception:
            pass

    return SubscriptionResponse(
        id=sub.id or 0,
        status=sub.current_status.value.lower(),
        is_trial=sub.is_trial,
        expire_at=sub.expire_at,
        days_left=_days_left(sub.expire_at),
        traffic_limit=sub.traffic_limit,
        device_limit=sub.device_limit,
        url=sub.url,
        plan_tag=sub.tag,
        used_traffic_bytes=used_bytes,
    )


@router.get(
    "/plans",
    response_model=list[PlanResponse],
    dependencies=[Depends(verify_internal_key)],
)
@inject
async def get_plans(
    plan_dao: FromDishka[PlanDao],
    user_dao: FromDishka[UserDao],
    get_available: FromDishka[GetAvailablePlans],
    telegram_id: int | None = None,
) -> list[PlanResponse]:
    trial = await plan_dao.get_active_trial_plans()

    # Без telegram_id вернуть можно только общедоступные планы: раньше
    # отдавались вообще все, и в кабинете каждый видел закрытые тарифы —
    # и с доступом по списку, и по ссылке.
    if telegram_id is None:
        regular = [p for p in await plan_dao.get_active_plans() if p.availability == PlanAvailability.ALL]
    else:
        user = await user_dao.get_by_telegram_id(telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        regular = await get_available.system(user)

    # Trial plans first, then regular — consistent with bot display order
    plans = trial + regular
    result = []
    for p in plans:
        durations = [
            PlanDurationResponse(
                id=d.id or 0,
                days=d.days,
                prices=[
                    PlanPriceResponse(
                        currency=pr.currency.value,
                        price=str(pr.price),
                    )
                    for pr in d.prices
                ],
            )
            for d in p.durations
        ]
        result.append(
            PlanResponse(
                id=p.id or 0,
                name=p.name,
                type=p.type.value.lower(),
                traffic_limit=p.traffic_limit,
                device_limit=p.device_limit,
                availability=p.availability.value.lower(),
                allowed_user_ids=p.allowed_telegram_ids or [],
                durations=durations,
            )
        )
    return result


@router.get(
    "/users/{telegram_id}/plans",
    response_model=list[PlanResponse],
    dependencies=[Depends(verify_internal_key)],
)
@inject
async def get_user_plans(
    telegram_id: int,
    user_dao: FromDishka[UserDao],
    plan_dao: FromDishka[PlanDao],
    get_available_plans: FromDishka[GetAvailablePlans],
    get_available_trial: FromDishka[GetAvailableTrial],
    trial_tag: str | None = None,
) -> list[PlanResponse]:
    user = await user_dao.get_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    regular = await get_available_plans.system(user)

    if trial_tag:
        # Свой пробный период вызывающей стороны: пробный план в боте может
        # быть только один, поэтому короткий период для сайта заведён обычным
        # планом с доступом по ссылке. Ищем его по тегу и отдаём по тому же
        # условию, по которому активация его и выдаст, — иначе кабинет
        # показывал бы чужой план на 7 дней, а выдавал свой на один.
        wanted = trial_tag.strip().lower()
        candidates = await plan_dao.get_active_trial_plans()
        candidates += await plan_dao.get_active_plans()
        tagged = next((p for p in candidates if (p.tag or "").strip().lower() == wanted), None)
        trial = tagged if user.is_trial_available else None
    else:
        trial = await get_available_trial.system(user)

    plans = ([trial] if trial else []) + (regular or [])

    result = []
    for p in plans:
        durations = [
            PlanDurationResponse(
                id=d.id or 0,
                days=d.days,
                prices=[
                    PlanPriceResponse(
                        currency=pr.currency.value,
                        price=str(pr.price),
                    )
                    for pr in d.prices
                ],
            )
            for d in p.durations
        ]
        result.append(
            PlanResponse(
                id=p.id or 0,
                name=p.name,
                type=p.type.value.lower(),
                traffic_limit=p.traffic_limit,
                device_limit=p.device_limit,
                availability=p.availability.value.lower(),
                allowed_user_ids=p.allowed_telegram_ids or [],
                durations=durations,
            )
        )
    return result


@router.get(
    "/transactions/{telegram_id}",
    response_model=list[TransactionResponse],
    dependencies=[Depends(verify_internal_key)],
)
@inject
async def get_transactions(
    telegram_id: int,
    transaction_dao: FromDishka[TransactionDao],
    user_dao: FromDishka[UserDao],
) -> list[TransactionResponse]:
    # get_by_user ждёт внутренний id пользователя, а не telegram_id:
    # передача telegram_id молча возвращала пустой список.
    user = await user_dao.get_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    transactions = await transaction_dao.get_by_user(user.id or 0)
    return [
        TransactionResponse(
            payment_id=str(t.payment_id),
            status=t.status.value.lower(),
            purchase_type=t.purchase_type.value.lower(),
            gateway_type=t.gateway_type.value.lower(),
            currency=t.currency.value,
            amount=str(t.pricing.final_amount) if t.pricing else None,
            created_at=t.created_at or datetime.now(timezone.utc),
        )
        for t in transactions
    ]


class ReferralEntryResponse(BaseModel):
    username: str | None
    name: str
    level: int
    joined_at: datetime


class ReferralStatsResponse(BaseModel):
    referral_code: str
    invited_count: int
    earned_days: int
    referrals: list[ReferralEntryResponse]


@router.get(
    "/referrals/{telegram_id}",
    response_model=ReferralStatsResponse,
    dependencies=[Depends(verify_internal_key)],
)
@inject
async def get_referral_stats(
    telegram_id: int,
    user_dao: FromDishka[UserDao],
    referral_dao: FromDishka[ReferralDao],
) -> ReferralStatsResponse:
    user = await user_dao.get_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    referrals = await referral_dao.get_referrals_list(user.id or 0)
    # Метода get_total_rewards_amount в ReferralDao нет — обращение к нему
    # роняло весь эндпоинт с AttributeError, и кабинет показывал пустую
    # страницу рефералов вместо статистики.
    stats = await referral_dao.get_user_referral_stats(user.id or 0)
    earned_days = stats.reward_days

    entries = [
        ReferralEntryResponse(
            username=ref.referred.username,
            name=ref.referred.name or "",
            level=int(ref.level),
            joined_at=ref.referred.created_at or datetime.now(timezone.utc),
        )
        for ref in referrals
    ]

    return ReferralStatsResponse(
        referral_code=user.referral_code or "",
        invited_count=len(entries),
        earned_days=earned_days,
        referrals=entries,
    )


@router.get(
    "/nodes",
    response_model=list[NodeResponse],
    dependencies=[Depends(verify_internal_key)],
)
@inject
async def get_nodes(
    sdk: FromDishka[RemnawaveSDK],
) -> list[NodeResponse]:
    try:
        nodes = await sdk.nodes.get_all()
        return [
            NodeResponse(
                uuid=str(getattr(n, "uuid", "")),
                name=getattr(n, "name", ""),
                address=getattr(n, "address", getattr(n, "host", "")),
                is_disabled=getattr(n, "is_disabled", False),
            )
            for n in (nodes or [])
        ]
    except Exception:
        return []


class AddDaysRequest(BaseModel):
    days: int


class SetDiscountRequest(BaseModel):
    discount: int  # 0–100


class SetDiscountResponse(BaseModel):
    discount: int


@router.patch(
    "/users/{telegram_id}/set-discount",
    response_model=SetDiscountResponse,
    dependencies=[Depends(verify_internal_key)],
)
@inject
async def set_user_discount(
    telegram_id: int,
    body: SetDiscountRequest,
    user_dao: FromDishka[UserDao],
    set_discount: FromDishka[SetUserPersonalDiscount],
) -> SetDiscountResponse:
    if not (0 <= body.discount <= 100):
        raise HTTPException(status_code=400, detail="discount must be 0–100")

    user = await user_dao.get_by_telegram_id(telegram_id)
    if not user or user.id is None:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        await set_discount.system(SetUserPersonalDiscountDto(user_id=user.id, discount=body.discount))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return SetDiscountResponse(discount=body.discount)


class AddDaysResponse(BaseModel):
    days_added: int


@router.post(
    "/subscriptions/{telegram_id}/add-days",
    response_model=AddDaysResponse,
    dependencies=[Depends(verify_internal_key)],
)
@inject
async def add_subscription_days(
    telegram_id: int,
    body: AddDaysRequest,
    user_dao: FromDishka[UserDao],
    add_duration: FromDishka[AddSubscriptionDuration],
) -> AddDaysResponse:
    if body.days <= 0:
        raise HTTPException(status_code=400, detail="days must be positive")

    # DTO ждёт локальный id пользователя, а снаружи приходит telegram_id —
    # как и в остальных эндпоинтах файла, резолвим его здесь.
    user = await user_dao.get_by_telegram_id(telegram_id)
    if not user or user.id is None:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        await add_duration.system(AddSubscriptionDurationDto(user_id=user.id, days=body.days))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return AddDaysResponse(days_added=body.days)


class ActivateFreePlanResponse(BaseModel):
    url: str | None
    expire_at: datetime | None
    days_left: int


@router.post(
    "/subscriptions/{telegram_id}/activate-free",
    response_model=ActivateFreePlanResponse,
    dependencies=[Depends(verify_internal_key)],
)
@inject
async def activate_free_plan(
    telegram_id: int,
    activate_free: FromDishka[ActivateFreePlan],
    user_dao: FromDishka[UserDao],
    plan_tag: str | None = None,
) -> ActivateFreePlanResponse:
    user = await user_dao.get_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        sub = await activate_free.system(
            ActivateFreePlanDto(telegram_id=telegram_id, plan_tag=plan_tag)
        )
    except ValueError as e:
        msg = str(e)
        status_code = 404 if "not found" in msg.lower() else 409
        raise HTTPException(status_code=status_code, detail=msg)
    return ActivateFreePlanResponse(
        url=sub.url,
        expire_at=sub.expire_at,
        days_left=_days_left(sub.expire_at),
    )


@router.get(
    "/subscriptions/{telegram_id}/devices",
    response_model=list[DeviceResponse],
    dependencies=[Depends(verify_internal_key)],
)
@inject
async def get_user_devices(
    telegram_id: int,
    subscription_dao: FromDishka[SubscriptionDao],
    remnawave: FromDishka[Remnawave],
) -> list[DeviceResponse]:
    sub = await subscription_dao.get_current_by_telegram_id(telegram_id)
    if not sub or not sub.user_remna_id:
        raise HTTPException(status_code=404, detail="No active subscription found")
    devices = await remnawave.get_devices(sub.user_remna_id)
    return [
        DeviceResponse(
            hwid=d.hwid,
            platform=getattr(d, "platform", None),
            device_model=getattr(d, "device_model", None),
        )
        for d in (devices or [])
    ]


@router.delete(
    "/subscriptions/{telegram_id}/devices/{hwid}",
    status_code=204,
    dependencies=[Depends(verify_internal_key)],
)
@inject
async def delete_user_device(
    telegram_id: int,
    hwid: str,
    delete_device: FromDishka[DeleteUserDevice],
    user_dao: FromDishka[UserDao],
) -> None:
    user = await user_dao.get_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        await delete_device.system(DeleteUserDeviceDto(user_id=user.id or 0, hwid=hwid))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "/subscriptions/{telegram_id}/reissue",
    status_code=204,
    dependencies=[Depends(verify_internal_key)],
)
@inject
async def reissue_subscription(
    telegram_id: int,
    reissue: FromDishka[ReissueSubscription],
    user_dao: FromDishka[UserDao],
) -> None:
    user = await user_dao.get_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        await reissue(user, None)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


class CreateUserRequest(BaseModel):
    telegram_id: int
    username: str | None = None
    name: str
    # Код рекламной или реферальной ссылки, по которой человек пришёл.
    # Сайт достаёт его из cookie, поставленной посадочной страницей.
    attribution_code: str | None = None


class CreateUserResponse(BaseModel):
    telegram_id: int
    created: bool


@router.post(
    "/users",
    response_model=CreateUserResponse,
    dependencies=[Depends(verify_internal_key)],
)
@inject
async def create_user(
    body: CreateUserRequest,
    user_dao: FromDishka[UserDao],
    ad_link_dao: FromDishka[AdLinkDao],
    referral_dao: FromDishka[ReferralDao],
    uow: FromDishka[UnitOfWork],
) -> CreateUserResponse:
    existing = await user_dao.get_by_telegram_id(body.telegram_id)
    if existing:
        return CreateUserResponse(telegram_id=body.telegram_id, created=False)

    referral_code = hashlib.sha256(str(body.telegram_id).encode()).hexdigest()[:8]
    user_dto = UserDto(
        telegram_id=body.telegram_id,
        name=body.name,
        username=body.username,
        referral_code=referral_code,
    )
    async with uow:
        created = await user_dao.create(user_dto)
        await uow.commit()

    if body.attribution_code:
        await _attach_attribution(
            body.attribution_code,
            created or user_dto,
            body.telegram_id,
            ad_link_dao,
            user_dao,
            referral_dao,
            uow,
        )

    return CreateUserResponse(telegram_id=body.telegram_id, created=True)


async def _attach_attribution(
    code: str,
    new_user: UserDto,
    telegram_id: int,
    ad_link_dao: AdLinkDao,
    user_dao: UserDao,
    referral_dao: ReferralDao,
    uow: UnitOfWork,
) -> None:
    """
    Привязывает свежего пользователя к рекламной ссылке или пригласившему.

    Раньше это умел только deep link в боте, и человек, пришедший по той же
    ссылке, но зарегистрировавшийся на сайте, для рекламы не существовал:
    переход был, а в воронке ноль. Отсюда же вырастут партнёрские выплаты —
    без этой привязки платить будет не за что.

    Сбой привязки не отменяет регистрацию: аккаунт уже создан, и потерять
    его из-за неудачной записи в статистику было бы хуже.
    """
    try:
        link = await ad_link_dao.get_by_code(code)
        if link is not None and link.is_active:
            async with uow:
                await ad_link_dao.register_user_click(link.id, telegram_id)
                await uow.commit()
            logger.info(f"Attribution: user '{telegram_id}' attached to ad link '{code}'")
            return

        referrer = await user_dao.get_by_referral_code(code)
        if referrer is not None and referrer.id != new_user.id:
            existing = await referral_dao.get_by_referred_id(new_user.id or 0)
            if existing is None:
                async with uow:
                    await referral_dao.create_referral(
                        ReferralDto(
                            level=ReferralLevel.FIRST,
                            referrer=referrer,
                            referred=new_user,
                        )
                    )
                    await uow.commit()
                logger.info(f"Attribution: user '{telegram_id}' attached to referrer '{code}'")
            return

        logger.debug(f"Attribution: code '{code}' not found, nothing attached")
    except Exception as e:
        logger.warning(f"Attribution by code '{code}' failed for '{telegram_id}': {e}")


@router.delete(
    "/users/{telegram_id}",
    status_code=204,
    dependencies=[Depends(verify_internal_key)],
)
@inject
async def delete_user(
    telegram_id: int,
    user_dao: FromDishka[UserDao],
    subscription_dao: FromDishka[SubscriptionDao],
    sdk: FromDishka[RemnawaveSDK],
    uow: FromDishka[UnitOfWork],
) -> None:
    user = await user_dao.get_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # 1. Delete VPN account from Remnawave panel
    sub = await subscription_dao.get_current_by_telegram_id(telegram_id)
    if sub and sub.user_remna_id:
        try:
            await sdk.users.delete_user(uuid=str(sub.user_remna_id))
        except Exception:
            pass  # Continue even if Remnawave is unavailable

    # 2. Delete user from bot database
    # delete() принимает внутренний id, telegram_id здесь не подходит.
    async with uow:
        await user_dao.delete(user.id or 0)
        await uow.commit()


class MigrateTelegramRequest(BaseModel):
    new_telegram_id: int


class MigrateTelegramResponse(BaseModel):
    migrated: bool
    message: str


@router.post(
    "/users/{old_telegram_id}/migrate-telegram",
    response_model=MigrateTelegramResponse,
    dependencies=[Depends(verify_internal_key)],
)
@inject
async def migrate_telegram(
    old_telegram_id: int,
    body: MigrateTelegramRequest,
    user_dao: FromDishka[UserDao],
    subscription_dao: FromDishka[SubscriptionDao],
    remnawave: FromDishka[Remnawave],
    add_duration: FromDishka[AddSubscriptionDuration],
    sdk: FromDishka[RemnawaveSDK],
    uow: FromDishka[UnitOfWork],
) -> MigrateTelegramResponse:
    user = await user_dao.get_by_telegram_id(old_telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    conflict = await user_dao.get_by_telegram_id(body.new_telegram_id)
    if conflict:
        # Real Telegram account already exists in bot (user interacted with bot before).
        # Transfer virtual user's subscription to the real account so it isn't lost.
        virtual_sub = await subscription_dao.get_current_by_telegram_id(old_telegram_id)
        real_sub = await subscription_dao.get_current_by_telegram_id(body.new_telegram_id)

        # Если у телеграм-аккаунта своей подписки нет, переносим веб-подписку
        # целиком: у неё сохраняется тот же user_remna_id, а значит и ссылка,
        # которую человек уже добавил в приложение, продолжает работать.
        carried_days = 0
        if virtual_sub and virtual_sub.id and not real_sub:
            async with uow:
                await user_dao.set_current_subscription_by_id(conflict.id or 0, virtual_sub.id)
                await user_dao.delete(user.id or 0)
                await uow.commit()

            try:
                await remnawave.update_user(user=conflict, uuid=str(virtual_sub.user_remna_id))
            except Exception:
                pass

            return MigrateTelegramResponse(migrated=True, message="Merged with existing account")

        # Обе стороны с подписками. Раньше веб-подписка здесь просто исчезала
        # вместе с виртуальным аккаунтом — вместе с оплаченными днями.
        # Переносим остаток дней на телеграм-подписку.
        if virtual_sub and real_sub:
            carried_days = _days_left(virtual_sub.expire_at)
            if carried_days > 0:
                try:
                    await add_duration.system(
                        AddSubscriptionDurationDto(
                            user_id=conflict.id or 0,
                            days=carried_days,
                        )
                    )
                except Exception:
                    # Перенос не удался — прерываем слияние, не удаляя ничего.
                    # Лучше оставить два аккаунта, чем стереть оплаченные дни.
                    raise HTTPException(
                        status_code=503,
                        detail="Не удалось перенести дни подписки. Привязка отменена, попробуйте позже.",
                    )

            # Лишний аккаунт в Remnawave надо убрать, иначе он продолжит
            # занимать место, а его старая ссылка — работать.
            if virtual_sub.user_remna_id:
                try:
                    await sdk.users.delete_user(uuid=str(virtual_sub.user_remna_id))
                except Exception:
                    pass

        async with uow:
            await user_dao.delete(user.id or 0)
            await uow.commit()

        message = (
            f"Merged with existing account, carried over {carried_days} days"
            if carried_days
            else "Merged with existing account"
        )
        return MigrateTelegramResponse(migrated=True, message=message)

    # No conflict — simple rename: update telegram_id on the virtual account
    sub = await subscription_dao.get_current_by_telegram_id(old_telegram_id)

    user.telegram_id = body.new_telegram_id
    async with uow:
        await user_dao.update(user)
        await uow.commit()

    # Update Remnawave username from remnashop{old_id} → remnashop{new_id} (best effort)
    if sub and sub.user_remna_id:
        try:
            await remnawave.update_user(user=user, uuid=str(sub.user_remna_id))
        except Exception:
            pass  # Don't fail the migration if Remnawave update fails

    return MigrateTelegramResponse(migrated=True, message="Migrated successfully")


# ---------------------------------------------------------------------------
# Node quota
# ---------------------------------------------------------------------------


class NodeQuotaResponse(BaseModel):
    enabled: bool
    limit_gb: float
    used_gb: float
    free_gb: float
    used_bytes: int
    is_restricted: bool
    period_start: datetime | None


@router.get(
    "/node-quota/{telegram_id}",
    response_model=NodeQuotaResponse,
    dependencies=[Depends(verify_internal_key)],
)
@inject
async def get_node_quota(
    telegram_id: int,
    node_quota_dao: FromDishka[NodeQuotaDao],
    config: FromDishka[AppConfig],
) -> NodeQuotaResponse:
    if not config.node_quota.enabled:
        return NodeQuotaResponse(
            enabled=False,
            limit_gb=0,
            used_gb=0,
            free_gb=0,
            used_bytes=0,
            is_restricted=False,
            period_start=None,
        )
    quota = await node_quota_dao.get_by_telegram_id(telegram_id)
    limit_gb = float(config.node_quota.monthly_limit_gb)
    used_bytes = quota.used_bytes if quota else 0
    used_gb = round(used_bytes / 1024**3, 2)
    free_gb = max(round(limit_gb - used_gb, 2), 0)
    return NodeQuotaResponse(
        enabled=True,
        limit_gb=limit_gb,
        used_gb=used_gb,
        free_gb=free_gb,
        used_bytes=used_bytes,
        is_restricted=quota.is_restricted if quota else False,
        period_start=quota.period_start if quota else None,
    )


# ---------------------------------------------------------------------------
# Payment gateways & web payments
# ---------------------------------------------------------------------------


class GatewayResponse(BaseModel):
    type: str
    currency: str


class CreateWebPaymentRequest(BaseModel):
    telegram_id: int
    plan_id: int
    duration_days: int
    gateway_type: str
    return_url: str
    # Подарочная покупка: оплаченная подписка уходит не плательщику, а в
    # одноразовый промокод. По умолчанию False — обычная покупка.
    is_gift: bool = False


class CreateWebPaymentResponse(BaseModel):
    payment_id: str
    payment_url: str | None


@router.get(
    "/gateways",
    response_model=list[GatewayResponse],
    dependencies=[Depends(verify_internal_key)],
)
@inject
async def get_active_gateways(
    gateway_dao: FromDishka[PaymentGatewayDao],
) -> list[GatewayResponse]:
    gateways = await gateway_dao.get_all(only_active=True)
    return [
        GatewayResponse(type=g.type.value.lower(), currency=g.currency.value)
        for g in gateways
        if g.type != PaymentGatewayType.TELEGRAM_STARS
    ]


@router.post(
    "/payments",
    response_model=CreateWebPaymentResponse,
    dependencies=[Depends(verify_internal_key)],
)
@inject
async def create_web_payment(
    body: CreateWebPaymentRequest,
    user_dao: FromDishka[UserDao],
    plan_dao: FromDishka[PlanDao],
    gateway_dao: FromDishka[PaymentGatewayDao],
    subscription_dao: FromDishka[SubscriptionDao],
    create_payment: FromDishka[CreatePayment],
) -> CreateWebPaymentResponse:
    user = await user_dao.get_by_telegram_id(body.telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    plan = await plan_dao.get_by_id(body.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    duration = plan.get_duration(body.duration_days)
    if not duration:
        raise HTTPException(status_code=404, detail=f"Duration {body.duration_days} days not found for this plan")

    try:
        gateway_type = PaymentGatewayType(body.gateway_type.upper())
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown gateway type: {body.gateway_type}")

    gateway = await gateway_dao.get_by_type(gateway_type)
    if not gateway or not gateway.is_active:
        raise HTTPException(status_code=400, detail=f"Gateway '{body.gateway_type}' is not active")

    base_price = duration.get_price(gateway.currency)
    discount = getattr(user, "personal_discount", 0) or 0
    final_amount = base_price * (100 - discount) / Decimal(100)

    pricing = PriceDetailsDto(
        original_amount=base_price,
        discount_percent=discount,
        final_amount=final_amount.quantize(Decimal("0.01")),
    )

    plan_snapshot = PlanSnapshotDto.from_plan(plan, body.duration_days)

    # Подарок не меняет подписку плательщика, поэтому и тип покупки у него
    # всегда NEW: CHANGE/RENEW описывали бы то, чего не происходит.
    subscription = await subscription_dao.get_current_by_telegram_id(body.telegram_id)
    if body.is_gift:
        purchase_type = PurchaseType.NEW
    elif subscription is None:
        purchase_type = PurchaseType.NEW
    elif subscription.plan_snapshot and subscription.plan_snapshot.id != plan.id:
        purchase_type = PurchaseType.CHANGE
    else:
        purchase_type = PurchaseType.RENEW

    try:
        result = await create_payment(
            user,
            CreatePaymentDto(
                plan_snapshot=plan_snapshot,
                pricing=pricing,
                purchase_type=purchase_type,
                gateway_type=gateway_type,
                return_url=body.return_url,
                is_gift=body.is_gift,
            ),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Payment creation failed: {e}")

    return CreateWebPaymentResponse(
        payment_id=str(result.id),
        payment_url=result.url,
    )


# ---------------------------------------------------------------------------
# Promocodes
# ---------------------------------------------------------------------------


class ActivatePromocodeRequest(BaseModel):
    code: str


class ActivatePromocodeResponse(BaseModel):
    code: str
    reward_type: str
    reward: str


@router.post(
    "/promocodes/{telegram_id}/activate",
    response_model=ActivatePromocodeResponse,
    dependencies=[Depends(verify_internal_key)],
)
@inject
async def activate_promocode(
    telegram_id: int,
    body: ActivatePromocodeRequest,
    user_dao: FromDishka[UserDao],
    activate: FromDishka[ActivatePromocode],
) -> ActivatePromocodeResponse:
    """
    Активация промокода бота из веб-кабинета.

    Коды заводятся в панели бота и должны действовать в обоих местах: свой
    список кодов на сайте означал бы две несвязанные системы и коды, которые
    работают где-то одном.
    """
    user = await user_dao.get_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        promo = await activate.system(ActivatePromocodeDto(code=body.code.strip(), user=user))
    except PromocodeError as e:
        # Отказ по промокоду — не сбой сервиса, а нормальный исход. Раньше
        # ловился только ValueError, а бот бросает свои исключения, поэтому
        # наружу уходила 500 и пользователь видел «не удалось активировать»
        # вместо настоящей причины.
        reasons = {
            PromocodeNotFoundError: "Промокод не найден",
            PromocodeExpiredError: "Срок действия промокода истёк",
            PromocodeAlreadyActivatedError: "Вы уже активировали этот промокод",
            PromocodeNotAvailableError: "Промокод недоступен",
        }
        # Порядок важен: PromocodeExpiredError наследует NotAvailable, и при
        # проверке по базовому классу истёкший код получил бы общий текст.
        detail = next(
            (msg for cls, msg in reasons.items() if isinstance(e, cls)),
            str(e) or "Промокод не может быть активирован",
        )
        raise HTTPException(status_code=400, detail=detail)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return ActivatePromocodeResponse(
        code=promo.code,
        reward_type=promo.reward_type.value.lower(),
        reward=str(promo.reward),
    )



# ---------------------------------------------------------------------------
# Подарочные подписки
# ---------------------------------------------------------------------------


class GiftCodeResponse(BaseModel):
    code: str
    plan_name: str
    duration_days: int
    expires_at: datetime


@router.get(
    "/gifts/{payment_id}",
    response_model=GiftCodeResponse,
    dependencies=[Depends(verify_internal_key)],
)
@inject
async def get_gift_code(
    payment_id: UUID,
    transaction_dao: FromDishka[TransactionDao],
    promocode_dao: FromDishka[PromocodeDao],
) -> GiftCodeResponse:
    """
    Код, выпущенный по оплаченному подарку.

    Сайт спрашивает эту ручку после возврата с оплаты: своего канала событий
    у него нет, а до подтверждения платежа кода ещё не существует.
    """
    transaction = await transaction_dao.get_by_payment_id(payment_id)
    if not transaction or not transaction.is_gift:
        raise HTTPException(status_code=404, detail="Gift payment not found")
    if transaction.status != TransactionStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="Payment is not completed yet")

    promo = await promocode_dao.get_by_code(gift_code_for_payment(payment_id))
    if not promo:
        raise HTTPException(status_code=404, detail="Gift code not issued")

    return GiftCodeResponse(
        code=promo.code,
        plan_name=transaction.plan_snapshot.name,
        duration_days=transaction.plan_snapshot.duration,
        expires_at=promo.expires_at,
    )


class PromocodeInfoResponse(BaseModel):
    code: str
    reward_type: str
    plan_name: str | None = None
    duration_days: int | None = None
    expires_at: datetime | None = None
    is_used: bool


@router.get(
    "/promocodes/{code}",
    response_model=PromocodeInfoResponse,
    dependencies=[Depends(verify_internal_key)],
)
@inject
async def get_promocode_info(
    code: str,
    promocode_dao: FromDishka[PromocodeDao],
) -> PromocodeInfoResponse:
    """
    Что внутри кода — для страницы получателя до входа в аккаунт.

    Активацию не выполняет: показывает содержимое, чтобы человек видел, что
    ему подарили, ещё до регистрации.
    """
    promo = await promocode_dao.get_by_code(code.strip().upper())
    if not promo or not promo.is_active:
        raise HTTPException(status_code=404, detail="Промокод не найден")

    used = 0
    if promo.id is not None:
        used = await promocode_dao.get_activations_count(promo.id)

    snapshot = promo.plan_snapshot or {}
    return PromocodeInfoResponse(
        code=promo.code,
        reward_type=promo.reward_type.value.lower(),
        plan_name=snapshot.get("name"),
        duration_days=snapshot.get("duration"),
        expires_at=promo.expires_at,
        is_used=bool(promo.max_activations and used >= promo.max_activations),
    )


class LinkLookupResponse(BaseModel):
    """Что стоит за кодом из рекламной или реферальной ссылки."""

    kind: str  # "ad" | "referral"
    code: str
    is_active: bool
    title: str | None = None
    telegram_url: str


@router.get(
    "/links/{code}",
    response_model=LinkLookupResponse,
    dependencies=[Depends(verify_internal_key)],
)
@inject
async def lookup_link(
    code: str,
    ad_link_dao: FromDishka[AdLinkDao],
    user_dao: FromDishka[UserDao],
    bot_service: FromDishka[BotService],
) -> LinkLookupResponse:
    """
    Разбор кода для посадочной страницы сайта.

    Реклама идёт не только внутри Telegram, и у нового человека его может
    не быть: ссылка ведёт на сайт, а сайт спрашивает здесь, что за код ему
    принесли. Коды остаются в базе бота — один источник правды.

    Ссылка на бота отдаётся готовой, чтобы сайту не пришлось повторять у
    себя правила сборки deep link.
    """
    ad_link = await ad_link_dao.get_by_code(code)
    if ad_link is not None:
        return LinkLookupResponse(
            kind="ad",
            code=code,
            is_active=ad_link.is_active,
            title=ad_link.name,
            telegram_url=await bot_service.get_ad_link_url(code),
        )

    referrer = await user_dao.get_by_referral_code(code)
    if referrer is not None:
        # Имя пригласившего наружу не отдаём: ссылку открывает посторонний
        # человек, и знать, кто его позвал, ему незачем.
        return LinkLookupResponse(
            kind="referral",
            code=code,
            is_active=True,
            title=None,
            telegram_url=await bot_service.get_referral_url(code),
        )

    raise HTTPException(status_code=404, detail="Link not found")


@router.post(
    "/links/{code}/visit",
    status_code=204,
    dependencies=[Depends(verify_internal_key)],
)
@inject
async def register_link_visit(
    code: str,
    ad_link_dao: FromDishka[AdLinkDao],
    uow: FromDishka[UnitOfWork],
) -> None:
    """
    Переход по ссылке засчитан на посадочной сайта.

    Человека здесь ещё нет — только визит, поэтому растёт лишь счётчик
    переходов. Привязка к пользователю происходит позже, при регистрации,
    когда появляется, к чему привязывать.
    """
    link = await ad_link_dao.get_by_code(code)
    if link is None or not link.is_active:
        return
    async with uow:
        await ad_link_dao.increment_clicks(link.id)
        await uow.commit()


class PartnerOverviewResponse(BaseModel):
    """
    Сводка для кабинета партнёра.

    Ни имён, ни telegram id приглашённых: партнёр видит числа и деньги, но
    не людей. Это и позиция по данным пользователей, и защита от того,
    чтобы базу можно было увести вместе с уходом партнёра.
    """

    rate_pct: float
    hold_days: int
    min_payout: float
    is_active: bool
    #
    pending: float
    available: float
    paid: float
    total: float
    payments_count: int
    #
    clicks: int
    signups: int
    links: list[dict]


@router.get(
    "/partners/{telegram_id}/overview",
    response_model=PartnerOverviewResponse,
    dependencies=[Depends(verify_internal_key)],
)
@inject
async def partner_overview(
    telegram_id: int,
    user_dao: FromDishka[UserDao],
    partner_dao: FromDishka[PartnerDao],
    ad_link_dao: FromDishka[AdLinkDao],
) -> PartnerOverviewResponse:
    user = await user_dao.get_by_telegram_id(telegram_id)
    if user is None or user.id is None:
        raise HTTPException(status_code=404, detail="User not found")

    partner = await partner_dao.get_by_user_id(user.id)
    if partner is None:
        raise HTTPException(status_code=404, detail="Not a partner")

    balance = await partner_dao.get_balance(partner.id)

    # Воронка собирается по ссылкам партнёра. Считаем по тем же данным, что
    # видит владелец в разделе рекламы, чтобы цифры у обеих сторон сходились.
    own_links = [ln for ln in await ad_link_dao.get_all() if ln.owner_user_id == user.id]
    links: list[dict] = []
    clicks = signups = 0
    for ln in own_links:
        stats = await ad_link_dao.get_stats(ln.id)
        clicks += ln.clicks_count
        signups += stats.unique_clicks
        links.append(
            {
                "code": ln.code,
                "name": ln.name,
                "is_active": ln.is_active,
                "clicks": ln.clicks_count,
                "signups": stats.unique_clicks,
                "trials": stats.trial_count,
                "paid": stats.paid_count,
            }
        )

    return PartnerOverviewResponse(
        rate_pct=float(partner.rate_pct),
        hold_days=partner.hold_days,
        min_payout=float(partner.min_payout),
        is_active=partner.is_active,
        pending=float(balance.pending),
        available=float(balance.available),
        paid=float(balance.paid),
        total=float(balance.total),
        payments_count=balance.payments_count,
        clicks=clicks,
        signups=signups,
        links=links,
    )


class CreatePartnerLinkRequest(BaseModel):
    name: str


class CreatePartnerLinkResponse(BaseModel):
    code: str


@router.post(
    "/partners/{telegram_id}/links",
    response_model=CreatePartnerLinkResponse,
    dependencies=[Depends(verify_internal_key)],
)
@inject
async def create_partner_link(
    telegram_id: int,
    body: CreatePartnerLinkRequest,
    create_link: FromDishka[CreatePartnerLink],
) -> CreatePartnerLinkResponse:
    """
    Партнёр заводит себе ссылку из кабинета на сайте.

    Кто именно партнёр, решается внутри по telegram_id: снаружи прийти
    может только сайт с внутренним ключом, но полагаться на это одно было
    бы неосторожно.
    """
    code = await create_link.system(
        CreatePartnerLinkDto(telegram_id=telegram_id, name=body.name)
    )
    if code is None:
        raise HTTPException(status_code=404, detail="Not a partner")
    return CreatePartnerLinkResponse(code=code)
