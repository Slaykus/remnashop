"""
Продление на другой тариф из кабинета — то же, что в боте.

Кабинет создавал покупку импортированного клиента как «смену тарифа»: срок
отсчитывался заново, и у того, кто платил заранее, остаток сгорал. Теперь,
если текущий тариф больше не продаётся, выбор нового тарифа проводится как
продление, а устройства сверх нового тарифа сохраняются докупкой.

Цену доплаты кабинет получает от бота и сам её не считает — здесь же
проверяется, что сумма платежа совпадает с той, что бот ему назвал.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace

from remnapy.enums.users import TrafficLimitStrategy

from src.application.services.pricing import PricingService
from src.core.enums import Currency, PlanType, PurchaseType
from src.web.endpoints.internal import (
    CreateWebPaymentRequest,
    create_web_payment,
    get_renewal_quote,
)

quote = get_renewal_quote.__dishka_orig_func__
pay = create_web_payment.__dishka_orig_func__

TG = 700000050


def _plan(pid: int, name: str, devices: int, rub: int):
    duration = SimpleNamespace(days=30, get_price=lambda currency, rub=rub: Decimal(rub))
    return SimpleNamespace(
        id=pid,
        name=name,
        tag=None,
        type=PlanType.DEVICES,
        traffic_limit_strategy=TrafficLimitStrategy.NO_RESET,
        traffic_limit=0,
        device_limit=devices,
        internal_squads=[],
        external_squad=None,
        is_trial=False,
        durations=[duration],
        get_duration=lambda days, d=duration: d if days == 30 else None,
    )


SOLO, DUO = _plan(2, "Solo", 2, 200), _plan(3, "Duo", 4, 360)
PLANS = [SOLO, DUO]


def _subscription(plan_id: int, devices: int, days_left: int = 150):
    return SimpleNamespace(
        is_trial=False,
        device_limit=devices,
        plan_snapshot=SimpleNamespace(id=plan_id),
        expire_at=datetime.now(timezone.utc) + timedelta(days=days_left),
    )


def _deps(subscription, captured: list):
    user = SimpleNamespace(id=50, log="[u]", personal_discount=0)

    async def get_user(tg):
        return user

    async def get_sub(tg):
        return subscription

    async def available(u):
        return PLANS

    async def match(dto):
        # Продаётся то, что есть в каталоге с тем же id.
        return next((p for p in PLANS if p.id == dto.plan_snapshot.id), None)

    async def get_plan(pid):
        return next(p for p in PLANS if p.id == pid)

    async def get_gateway(t):
        return SimpleNamespace(is_active=True, currency=Currency.RUB)

    async def create(u, dto):
        captured.append(dto)
        return SimpleNamespace(id="p-1", url="https://pay.invalid")

    async def noop(*a, **k):
        return None

    return dict(
        user_dao=SimpleNamespace(get_by_telegram_id=get_user),
        subscription_dao=SimpleNamespace(get_current_by_telegram_id=get_sub),
        get_available_plans=SimpleNamespace(system=available),
        match_plan=SimpleNamespace(system=match),
        pricing_service=PricingService(),
        plan_dao=SimpleNamespace(get_by_id=get_plan),
        gateway_dao=SimpleNamespace(get_by_type=get_gateway),
        create_payment=create,
        event_publisher=SimpleNamespace(publish=noop),
        config=SimpleNamespace(build=SimpleNamespace(data={})),
    )


def _quote_deps(subscription):
    d = _deps(subscription, [])
    return {k: d[k] for k in ("user_dao", "subscription_dao", "get_available_plans", "match_plan", "pricing_service")}


async def _pay(subscription, plan, keep=True):
    captured: list = []
    body = CreateWebPaymentRequest(
        telegram_id=TG, plan_id=plan.id, duration_days=30, gateway_type="yookassa",
        return_url="https://r.invalid", keep_devices=keep,
    )
    await pay(body=body, **_deps(subscription, captured))
    return captured[0]


# --- условия продления ---------------------------------------------------


async def test_quote_for_an_unsold_plan() -> None:
    q = await quote(telegram_id=TG, **_quote_deps(_subscription(-1, 4)))
    assert q.renew_new_plan is True
    assert q.current_devices == 4
    assert q.recommended_plan_id == 3  # Duo сохраняет все 4
    by_id = {p.plan_id: p for p in q.plans}
    assert by_id[2].keep_devices == 2
    assert by_id[2].durations[0].surcharge_rub == "160"  # 2 × 80
    assert by_id[3].keep_devices == 0


async def test_no_quote_while_the_plan_is_still_sold() -> None:
    q = await quote(telegram_id=TG, **_quote_deps(_subscription(2, 2)))
    assert q.renew_new_plan is False and q.plans == []


# --- платёж --------------------------------------------------------------


async def test_unsold_plan_becomes_a_renewal_with_kept_devices() -> None:
    dto = await _pay(_subscription(-1, 4), SOLO)
    assert dto.purchase_type == PurchaseType.RENEW
    assert dto.plan_snapshot.extra_devices == 2
    # Ровно та сумма, что назвала ручка условий: 200 + 160.
    assert dto.pricing.original_amount == Decimal(360)


async def test_declining_to_keep_devices_charges_the_plan_alone() -> None:
    dto = await _pay(_subscription(-1, 4), SOLO, keep=False)
    assert dto.purchase_type == PurchaseType.RENEW
    assert dto.plan_snapshot.extra_devices == 0
    assert dto.pricing.original_amount == Decimal(200)


async def test_plan_that_covers_the_devices_has_no_surcharge() -> None:
    dto = await _pay(_subscription(-1, 4), DUO)
    assert (dto.purchase_type, dto.plan_snapshot.extra_devices) == (PurchaseType.RENEW, 0)
    assert dto.pricing.original_amount == Decimal(360)


async def test_switching_from_a_sold_plan_is_still_a_change() -> None:
    # Ничего не поменялось для обычных клиентов: Solo -> Duo — это смена.
    dto = await _pay(_subscription(2, 2), DUO)
    assert dto.purchase_type == PurchaseType.CHANGE
    assert dto.plan_snapshot.extra_devices == 0


async def test_same_plan_is_an_ordinary_renewal() -> None:
    dto = await _pay(_subscription(2, 2), SOLO)
    assert dto.purchase_type == PurchaseType.RENEW
    assert dto.pricing.original_amount == Decimal(200)
