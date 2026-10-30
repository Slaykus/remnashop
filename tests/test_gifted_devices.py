"""
Устройства, выданные вручную, переживают продление и не входят в цену.

Владелец поднимал особым клиентам лимит в панели (Team на 10 устройств —
до 15). Бот узнавал новый лимит, но при продлении собирал его заново из
тарифа и докупленного — и клиент после оплаты оставался с 10. Подарок —
всё, что в лимите сверх тарифа и докупки; здесь проверяется, что он не
пропадает и что за него не начинают брать деньги.
"""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from remnapy.enums.users import TrafficLimitStrategy

from src.application.dto import (
    PlanSnapshotDto,
    PriceDetailsDto,
    SubscriptionDto,
    TransactionDto,
    UserDto,
)
from src.application.services.device_pricing import gifted_devices
from src.application.use_cases.subscription.commands.purchase import (
    PurchaseSubscription,
    PurchaseSubscriptionDto,
)
from src.core.enums import (
    Currency,
    PaymentGatewayType,
    PlanType,
    PurchaseType,
    SubscriptionStatus,
    TransactionStatus,
)

NOW = datetime.now(timezone.utc)


def _plan(plan_id: int, name: str, devices: int, days: int = 30) -> PlanSnapshotDto:
    return PlanSnapshotDto(
        id=plan_id,
        name=name,
        type=PlanType.DEVICES,
        traffic_limit=0,
        device_limit=devices,
        duration=days,
        traffic_limit_strategy=TrafficLimitStrategy.NO_RESET,
    )


TEAM, DUO, UNLIMITED = _plan(5, "Team", 10), _plan(3, "Duo", 4), _plan(9, "Unlimited", 0)


def _sub(plan=TEAM, devices: int = 15, extra: int = 0, trial: bool = False) -> SubscriptionDto:
    return SubscriptionDto(
        id=687,
        user_id=44,
        user_remna_id=uuid4(),
        traffic_limit=0,
        device_limit=devices,
        extra_devices=extra,
        traffic_limit_strategy=TrafficLimitStrategy.NO_RESET,
        expire_at=NOW + timedelta(days=10),
        url="https://example.invalid/sub",
        is_trial=trial,
        plan_snapshot=plan,
    )


async def _buy(subscription: SubscriptionDto, paid: PlanSnapshotDto, kind: PurchaseType):
    panel: dict = {}
    created: list = []

    class Uow:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def commit(self):
            pass

    async def update_user(**kw):
        source = kw.get("subscription") or kw.get("plan")
        panel["limit"] = source.device_limit
        return SimpleNamespace(
            uuid=subscription.user_remna_id,
            status=SubscriptionStatus.ACTIVE,
            expire_at=NOW + timedelta(days=30),
            subscription_url="https://example.invalid/sub",
        )

    async def create(subscription, user_id):
        created.append(subscription)

    async def noop(*a, **k):
        return None

    uc = PurchaseSubscription.__new__(PurchaseSubscription)
    uc.uow = Uow()
    uc.user_dao = SimpleNamespace(update=noop)
    uc.subscription_dao = SimpleNamespace(update=noop, update_status=noop, create=create)
    uc.remnawave = SimpleNamespace(update_user=update_user)
    user = UserDto(id=44, telegram_id=700000044, name="client")
    transaction = TransactionDto(
        id=1,
        payment_id=uuid4(),
        user_id=44,
        status=TransactionStatus.COMPLETED,
        purchase_type=kind,
        gateway_type=PaymentGatewayType.YOOKASSA,
        pricing=PriceDetailsDto.test(),
        currency=Currency.RUB,
        plan_snapshot=paid,
    )
    await uc._execute(user, PurchaseSubscriptionDto(user, transaction, subscription))
    result = created[0] if created else subscription
    assert panel["limit"] == result.device_limit, "в панель ушёл не тот лимит"
    return result


# --- сколько подарено ----------------------------------------------------


def test_gift_is_whatever_exceeds_plan_and_bought_devices() -> None:
    assert gifted_devices(_sub(devices=15)) == 5
    assert gifted_devices(_sub(devices=15, extra=2)) == 3
    assert gifted_devices(_sub(devices=10)) == 0
    assert gifted_devices(_sub(devices=8)) == 0  # урезанный лимит — не подарок


def test_imported_and_unlimited_limits_are_not_gifts() -> None:
    imported = replace(TEAM, id=-1, name="IMPORTED", device_limit=1)
    assert gifted_devices(_sub(plan=imported, devices=4)) == 0
    assert gifted_devices(_sub(plan=UNLIMITED, devices=15)) == 0
    assert gifted_devices(_sub(devices=0)) == 0


# --- продление -----------------------------------------------------------


async def test_renewal_keeps_the_gift() -> None:
    # Ровно случай клиента: Team, 15 вручную, продление — остаётся 15.
    sub = await _buy(_sub(devices=15), TEAM, PurchaseType.RENEW)
    assert (sub.device_limit, sub.extra_devices) == (15, 0)


async def test_renewal_keeps_gift_and_bought_devices_apart() -> None:
    sub = await _buy(_sub(devices=17, extra=2), TEAM, PurchaseType.RENEW)
    assert (sub.device_limit, sub.extra_devices) == (17, 2)


async def test_renewal_without_a_gift_is_unchanged() -> None:
    sub = await _buy(_sub(devices=10), TEAM, PurchaseType.RENEW)
    assert sub.device_limit == 10


async def test_renewal_onto_a_new_plan_does_not_count_the_gift_twice() -> None:
    # Прежний тариф не продаётся: всё сверх нового уже пришло в оплате.
    old = replace(TEAM, id=-1, name="IMPORTED", device_limit=1)
    paid = replace(DUO, extra_devices=0)
    sub = await _buy(_sub(plan=old, devices=4), paid, PurchaseType.RENEW)
    assert sub.device_limit == 4


# --- смена тарифа и докупка ---------------------------------------------


async def test_plan_change_carries_the_gift_over() -> None:
    sub = await _buy(_sub(devices=15), DUO, PurchaseType.CHANGE)
    assert sub.device_limit == 9  # 4 по тарифу + 5 подаренных
    assert sub.plan_snapshot.device_limit == 4  # снимок описывает тариф


async def test_change_to_unlimited_stays_unlimited() -> None:
    sub = await _buy(_sub(devices=15), UNLIMITED, PurchaseType.CHANGE)
    assert sub.device_limit == 0


async def test_trial_conversion_has_no_gift() -> None:
    trial = replace(TEAM, id=8, name="trial", device_limit=1, is_trial=True)
    sub = await _buy(_sub(plan=trial, devices=3, trial=True), DUO, PurchaseType.CHANGE)
    assert sub.device_limit == 4


async def test_buying_a_device_does_not_make_the_gift_paid() -> None:
    # Докупка одного устройства к 15: платным становится только оно.
    paid = replace(TEAM, device_limit=16, duration=10)
    sub = await _buy(_sub(devices=15), paid, PurchaseType.DEVICES)
    assert (sub.device_limit, sub.extra_devices) == (16, 1)
    assert gifted_devices(sub) == 5
