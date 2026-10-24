"""
Чей тариф остаётся при слиянии аккаунтов и до какого числа.

Ошибка здесь стоит денег клиента в обе стороны: понизить — отнять
оплаченное, перепутать сравнение — выдать не то. Поэтому каждый вывод
проверяется на числах из реальных случаев.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from src.application.services.account_merge import dominates, merged_expire_at, plan_source

NOW = datetime(2026, 10, 22, 1, 53, tzinfo=timezone.utc)
SOON = NOW + timedelta(days=150)


def sub(traffic: int, devices: int, *, expire_at: datetime = SOON, is_trial: bool = False):
    return SimpleNamespace(
        traffic_limit=traffic, device_limit=devices, expire_at=expire_at, is_trial=is_trial
    )


SOLO = sub(0, 2)  # безлимит, 2 устройства — как в каталоге
DUO = sub(0, 4)
IMPORTED_5GB = sub(5, 1)  # импортированная подписка: в снимке безлимит, на самой подписке 5 ГБ


def test_the_reported_case_takes_the_paid_plan() -> None:
    # Разобранный случай: в кабинете полгода Solo, в Telegram импортированный 5 ГБ / 1.
    assert plan_source(SOLO, IMPORTED_5GB, NOW) == "virtual"


def test_zero_means_unlimited_not_less() -> None:
    # Главная ловушка: max() по числам выбрал бы 5 вместо 0 и понизил бы
    # безлимит до пяти гигабайт.
    assert dominates(sub(0, 2), sub(5, 2))
    assert not dominates(sub(5, 2), sub(0, 2))


def test_unlimited_is_never_replaced_by_a_limited_plan() -> None:
    assert plan_source(sub(50, 2), sub(0, 2), NOW) == "real"


def test_a_better_telegram_plan_is_never_downgraded() -> None:
    # В Telegram Duo, в кабинете купили Solo: Duo остаётся, дни добавятся.
    assert plan_source(SOLO, DUO, NOW) == "real"


def test_equal_plans_keep_the_telegram_one() -> None:
    # Solo и Solo. Менять нечего, переносятся только дни.
    assert plan_source(SOLO, sub(0, 2), NOW) == "real"


def test_mixed_limits_take_nothing_away() -> None:
    # Один лучше по трафику, другой по устройствам. Выбрать за клиента нельзя,
    # остаётся тариф Telegram — у клиента ничего не отнимается.
    assert plan_source(sub(50, 4), sub(0, 1), NOW) == "real"


def test_expired_telegram_plan_gives_way() -> None:
    # Истёкший Duo не тариф: понижать в нём нечего.
    expired_duo = sub(0, 4, expire_at=NOW - timedelta(days=200))
    assert plan_source(SOLO, expired_duo, NOW) == "virtual"


def test_trial_does_not_block_a_paid_plan() -> None:
    generous_trial = sub(0, 6, is_trial=True)
    assert plan_source(SOLO, generous_trial, NOW) == "virtual"


def test_days_are_added_to_an_active_subscription() -> None:
    real_end = NOW + timedelta(days=10)
    assert merged_expire_at(real_end, 180, NOW) == real_end + timedelta(days=180)


def test_days_on_a_long_expired_subscription_land_in_the_future() -> None:
    # Раньше: дата полугодовой давности + 30 дней = снова прошлое, перенос
    # отказывал, и Telegram было не привязать.
    long_ago = NOW - timedelta(days=180)
    result = merged_expire_at(long_ago, 30, NOW)
    assert result == NOW + timedelta(days=30)
    assert result > NOW
