"""
Internal API for Rain VPN Web Personal Cabinet.

Endpoints protected by X-Internal-Key header (APP_WEB_API_KEY env var).
"""

from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timezone
from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from remnapy import RemnawaveSDK

from src.application.common import Remnawave
from decimal import Decimal

from src.application.common.dao import PlanDao, PaymentGatewayDao, ReferralDao, SubscriptionDao, TransactionDao, UserDao
from src.application.common.uow import UnitOfWork
from src.application.dto import UserDto
from src.application.dto.plan import PlanSnapshotDto
from src.application.dto.transaction import PriceDetailsDto
from src.application.use_cases.gateways.commands.payment import CreatePayment, CreatePaymentDto
from src.application.use_cases.subscription import AddSubscriptionDuration
from src.application.use_cases.subscription.commands.management import AddSubscriptionDurationDto
from src.application.use_cases.subscription.commands.purchase import ActivateFreePlan, ActivateFreePlanDto
from src.application.use_cases.user import SetUserPersonalDiscount
from src.application.use_cases.user.commands.profile_edit import SetUserPersonalDiscountDto
from src.core.enums import PaymentGatewayType, PurchaseType, ReferralRewardType
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
    durations: list[PlanDurationResponse]


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
    if expire_at is None:
        return 0
    now = datetime.now(timezone.utc)
    if expire_at.tzinfo is None:
        expire_at = expire_at.replace(tzinfo=timezone.utc)
    return max(int((expire_at - now).total_seconds() / 86400), 0)


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
    sub = await subscription_dao.get_current(telegram_id)
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
) -> list[PlanResponse]:
    regular = await plan_dao.get_active_plans()
    trial = await plan_dao.get_active_trial_plans()
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
) -> list[TransactionResponse]:
    transactions = await transaction_dao.get_by_user(telegram_id)
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
    earned_days = await referral_dao.get_total_rewards_amount(
        telegram_id, ReferralRewardType.EXTRA_DAYS
    )

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
    set_discount: FromDishka[SetUserPersonalDiscount],
) -> SetDiscountResponse:
    if not (0 <= body.discount <= 100):
        raise HTTPException(status_code=400, detail="discount must be 0–100")
    try:
        await set_discount.system(SetUserPersonalDiscountDto(telegram_id=telegram_id, discount=body.discount))
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
    add_duration: FromDishka[AddSubscriptionDuration],
) -> AddDaysResponse:
    if body.days <= 0:
        raise HTTPException(status_code=400, detail="days must be positive")
    try:
        await add_duration.system(AddSubscriptionDurationDto(telegram_id=telegram_id, days=body.days))
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
) -> ActivateFreePlanResponse:
    user = await user_dao.get_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        sub = await activate_free.system(ActivateFreePlanDto(telegram_id=telegram_id))
    except ValueError as e:
        msg = str(e)
        status_code = 404 if "not found" in msg.lower() else 409
        raise HTTPException(status_code=status_code, detail=msg)
    return ActivateFreePlanResponse(
        url=sub.url,
        expire_at=sub.expire_at,
        days_left=_days_left(sub.expire_at),
    )


class CreateUserRequest(BaseModel):
    telegram_id: int
    username: str | None = None
    name: str


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
        await user_dao.create(user_dto)
        await uow.commit()
    return CreateUserResponse(telegram_id=body.telegram_id, created=True)


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
    sub = await subscription_dao.get_current(telegram_id)
    if sub and sub.user_remna_id:
        try:
            await sdk.users.delete_user(uuid=str(sub.user_remna_id))
        except Exception:
            pass  # Continue even if Remnawave is unavailable

    # 2. Delete user from bot database
    async with uow:
        await user_dao.delete(telegram_id)
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
    uow: FromDishka[UnitOfWork],
) -> MigrateTelegramResponse:
    user = await user_dao.get_by_telegram_id(old_telegram_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    conflict = await user_dao.get_by_telegram_id(body.new_telegram_id)
    if conflict:
        # Real Telegram account already exists in bot (user interacted with bot before).
        # Transfer virtual user's subscription to the real account so it isn't lost.
        virtual_sub = await subscription_dao.get_current(old_telegram_id)
        real_sub = await subscription_dao.get_current(body.new_telegram_id)

        async with uow:
            if virtual_sub and virtual_sub.id and not real_sub:
                # Move subscription reference from virtual user to real user
                await user_dao.set_current_subscription(body.new_telegram_id, virtual_sub.id)
            # Remove the virtual account — real account takes over
            await user_dao.delete(old_telegram_id)
            await uow.commit()

        # Update Remnawave username to reflect real telegram_id (best effort)
        if virtual_sub and virtual_sub.user_remna_id and not real_sub:
            try:
                await remnawave.update_user(user=conflict, uuid=str(virtual_sub.user_remna_id))
            except Exception:
                pass

        return MigrateTelegramResponse(migrated=True, message="Merged with existing account")

    # No conflict — simple rename: update telegram_id on the virtual account
    sub = await subscription_dao.get_current(old_telegram_id)

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

    subscription = await subscription_dao.get_current(body.telegram_id)
    if subscription is None:
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
            ),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Payment creation failed: {e}")

    return CreateWebPaymentResponse(
        payment_id=str(result.id),
        payment_url=result.url,
    )
