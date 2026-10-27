"""
Продление, когда текущий тариф больше не продаётся.

Импортированные из старой системы подписки (тариф IMPORTED, id -1) не
продлевались вовсе: «Продлить» показывал «план устарел» и никуда не вёл,
а «Изменить» отсчитывает срок заново и сжигает остаток. 256 таких подписок
истекают в марте 2027-го разом.

Теперь человек выбирает тариф, и выбор проводится как продление. Главное,
что здесь проверяется, — деньги и устройства: дни добавляются к сроку, а
не заменяют его; устройства молча не отнимаются; повторное продление на
новом тарифе работает как обычное.
"""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from adaptix import Retort

from src.application.dto import (
    PlanSnapshotDto,
    PriceDetailsDto,
    SubscriptionDto,
    TransactionDto,
    UserDto,
)
from src.application.services.device_pricing import devices_to_keep
from src.application.use_cases.subscription.commands.purchase import (
    PurchaseSubscription,
    PurchaseSubscriptionDto,
)
from remnapy.enums.users import TrafficLimitStrategy

from src.core.enums import (
    Currency,
    PaymentGatewayType,
    PlanType,
    PurchaseType,
    TransactionStatus,
)
from src.telegram.routers.subscription.getters import (
    _recommended_plan_id,
    renew_devices_notice,
    renewal_extra_devices,
)
from src.telegram.routers.subscription.handlers import _resolve_renew_plan

NOW = datetime.now(timezone.utc)


def _snapshot(plan_id: int, name: str, devices: int, traffic: int = 0, days: int = 30, extra: int = 0):
    return PlanSnapshotDto(
        id=plan_id,
        name=name,
        type=PlanType.DEVICES,
        traffic_limit=traffic,
        device_limit=devices,
        duration=days,
        traffic_limit_strategy=TrafficLimitStrategy.NO_RESET,
        extra_devices=extra,
    )


IMPORTED = _snapshot(-1, "IMPORTED", 4)


def _subscription(expire_at: datetime, snapshot=IMPORTED, devices: int = 4, extra: int = 0):
    return SubscriptionDto(
        id=49,
        user_id=50,
        user_remna_id=uuid4(),
        traffic_limit=snapshot.traffic_limit,
        device_limit=devices,
        extra_devices=extra,
        traffic_limit_strategy=TrafficLimitStrategy.NO_RESET,
        expire_at=expire_at,
        url="https://example.invalid/sub",
        plan_snapshot=snapshot,
    )


def _transaction(snapshot: PlanSnapshotDto) -> TransactionDto:
    return TransactionDto(
        id=1,
        payment_id=uuid4(),
        user_id=50,
        status=TransactionStatus.COMPLETED,
        purchase_type=PurchaseType.RENEW,
        gateway_type=PaymentGatewayType.YOOKASSA,
        pricing=PriceDetailsDto.test(),
        currency=Currency.RUB,
        plan_snapshot=snapshot,
    )


async def _renew(subscription: SubscriptionDto, paid: PlanSnapshotDto) -> SubscriptionDto:
    panel = {}

    class Uow:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def commit(self):
            pass

    async def update_user(**kw):
        panel["limit"] = kw["subscription"].device_limit

    async def noop(*a, **k):
        return None

    uc = PurchaseSubscription.__new__(PurchaseSubscription)
    uc.uow = Uow()
    uc.user_dao = SimpleNamespace(update=noop)
    uc.subscription_dao = SimpleNamespace(update=noop)
    uc.remnawave = SimpleNamespace(update_user=update_user)
    user = UserDto(id=50, telegram_id=700000001, name="client")
    await uc._execute(user, PurchaseSubscriptionDto(user, _transaction(paid), subscription))
    assert panel["limit"] == subscription.device_limit, "в панель ушёл не тот лимит"
    return subscription


# ---------------------------------------------------------------------------
# Деньги и срок
# ---------------------------------------------------------------------------


async def test_active_subscription_keeps_its_remaining_days() -> None:
    # Платит вперёд, пока IMPORTED ещё действует: остаток не сгорает.
    end = NOW + timedelta(days=150)
    sub = await _renew(_subscription(end), _snapshot(3, "Duo", 4))
    assert sub.expire_at == end + timedelta(days=30)


async def test_expired_subscription_counts_from_today() -> None:
    sub = await _renew(_subscription(NOW - timedelta(days=2)), _snapshot(3, "Duo", 4))
    assert NOW + timedelta(days=29) < sub.expire_at <= NOW + timedelta(days=30, seconds=5)


async def test_new_plan_replaces_the_imported_limits() -> None:
    sub = _subscription(NOW + timedelta(days=10), _snapshot(-1, "IMPORTED", 1, traffic=5), devices=1)
    sub.traffic_limit = 5
    await _renew(sub, _snapshot(2, "Solo", 2))
    assert (sub.traffic_limit, sub.device_limit, sub.plan_snapshot.name) == (0, 2, "Solo")


async def test_kept_devices_arrive_with_the_payment() -> None:
    # Solo + 2 сохранённых: в снимке оплаты едут 2, итог — те же 4.
    sub = await _renew(_subscription(NOW), _snapshot(2, "Solo", 2, extra=2))
    assert (sub.device_limit, sub.extra_devices) == (4, 2)


async def test_subscription_snapshot_describes_the_plan_not_the_payment() -> None:
    sub = await _renew(_subscription(NOW), _snapshot(2, "Solo", 2, extra=2))
    assert sub.plan_snapshot.extra_devices == 0
    assert sub.plan_snapshot.id == 2


async def test_dropping_devices_leaves_only_the_plan_limit() -> None:
    sub = await _renew(_subscription(NOW), _snapshot(2, "Solo", 2, extra=0))
    assert (sub.device_limit, sub.extra_devices) == (2, 0)


async def test_ordinary_renewal_keeps_bought_devices_from_the_database() -> None:
    # Обычное продление того же тарифа: счётчик берётся из подписки, а не
    # из снимка оплаты (там ноль) — иначе докупленное сгорало бы.
    solo = _snapshot(2, "Solo", 2)
    sub = await _renew(_subscription(NOW, snapshot=solo, devices=3, extra=1), solo)
    assert (sub.device_limit, sub.extra_devices) == (3, 1)


# ---------------------------------------------------------------------------
# Устройства: что докупать и что советовать
# ---------------------------------------------------------------------------


def test_devices_to_keep() -> None:
    assert devices_to_keep(4, 2) == 2
    assert devices_to_keep(2, 2) == 0
    assert devices_to_keep(1, 2) == 0
    assert devices_to_keep(4, 0) == 0  # безлимитный тариф покрывает всё
    assert devices_to_keep(0, 2) == 0  # безлимит докупкой не сохранить
    assert devices_to_keep(12, 2) == 8  # не выше потолка докупки


def _plans():
    def p(pid, devices):
        return SimpleNamespace(id=pid, device_limit=devices)

    return [p(2, 2), p(3, 4), p(4, 6), p(5, 10)]


def test_recommended_plan_keeps_every_device() -> None:
    assert _recommended_plan_id(_plans(), 4) == 3  # Duo
    assert _recommended_plan_id(_plans(), 1) == 2  # Solo
    assert _recommended_plan_id(_plans(), 3) == 3  # Duo, а не Solo
    assert _recommended_plan_id(_plans(), 10) == 5  # Team
    assert _recommended_plan_id(_plans(), 0) is None  # безлимит не покрыть


def _manager(**data):
    return SimpleNamespace(dialog_data=data)


def test_notice_keeps_devices_by_default() -> None:
    m = _manager(renew_new_plan=True, current_devices=4, keep_devices=True, PlanDto={"device_limit": 2})
    n = renew_devices_notice(m)
    assert (n["devices_notice"], n["devices_warning"], n["keep_count"]) == ("KEEP", "HIDE", 2)


def test_notice_warns_before_payment_when_devices_are_dropped() -> None:
    m = _manager(renew_new_plan=True, current_devices=4, keep_devices=False, PlanDto={"device_limit": 2})
    n = renew_devices_notice(m)
    assert (n["devices_notice"], n["devices_warning"]) == ("DROP", "SHOW")


def test_no_notice_when_the_plan_covers_the_devices() -> None:
    m = _manager(renew_new_plan=True, current_devices=1, keep_devices=True, PlanDto={"device_limit": 2})
    assert renew_devices_notice(m)["devices_notice"] == "NONE"


def test_no_notice_on_an_ordinary_renewal() -> None:
    assert renew_devices_notice(_manager(PlanDto={"device_limit": 2}))["devices_notice"] == "NONE"


async def test_price_includes_kept_devices_only_when_keeping() -> None:
    base = dict(purchase_type=PurchaseType.RENEW, renew_new_plan=True, current_devices=4, PlanDto={"device_limit": 2})
    dao = SimpleNamespace()
    assert await renewal_extra_devices(_manager(**base, keep_devices=True), dao, None) == 2
    assert await renewal_extra_devices(_manager(**base, keep_devices=False), dao, None) == 0


# ---------------------------------------------------------------------------
# Вход в продление и совместимость
# ---------------------------------------------------------------------------


async def test_unsold_plan_opens_the_choice_instead_of_a_dead_end() -> None:
    notified = []

    async def match(dto):
        return None

    async def notify(*a, **k):
        notified.append(k.get("i18n_key"))

    m = _manager()
    handled = await _resolve_renew_plan(
        SimpleNamespace(log="[u]"),
        m,
        _subscription(NOW - timedelta(days=1)),
        [SimpleNamespace(id=2, device_limit=2)],
        SimpleNamespace(system=match),
        SimpleNamespace(notify_user=notify),
        Retort(),
    )
    # «Не обработано» — вызывающий покажет список тарифов.
    assert handled is False
    assert m.dialog_data == {"renew_new_plan": True, "current_devices": 4, "keep_devices": True}
    assert notified == []  # больше никакого «план устарел»


def test_old_snapshots_without_the_new_field_still_load() -> None:
    # В базе сотни снимков без extra_devices — они обязаны читаться.
    raw = Retort().dump(_snapshot(2, "Solo", 2))
    raw.pop("extra_devices")
    assert Retort().load(raw, PlanSnapshotDto).extra_devices == 0


def test_renewal_matching_ignores_the_payment_only_field() -> None:
    from src.application.use_cases.plan.queries.match import MatchPlan

    plan = SimpleNamespace(
        id=2,
        type=PlanType.DEVICES,
        traffic_limit=0,
        device_limit=2,
        traffic_limit_strategy=TrafficLimitStrategy.NO_RESET,
        internal_squads=[],
        external_squad=None,
    )
    snapshot = replace(_snapshot(2, "Solo", 2), extra_devices=2)
    assert MatchPlan._is_plan_equal(None, snapshot, plan)  # type: ignore[arg-type]
