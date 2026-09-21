"""
Цена устройств сверх базовых двух.

Главная проверка здесь — предпоследняя: формула обязана давать ровно те
цены, что стоят у тарифов-пресетов. Если они разойдутся, у одного и того
же набора устройств появятся две цены, и рано или поздно двое клиентов
это сравнят.
"""

from decimal import Decimal

import pytest

from src.application.services.device_pricing import (
    BASE_DEVICES,
    extra_devices_price,
    monthly_extra_price,
    monthly_rate,
)


@pytest.mark.parametrize(
    ("device_index", "expected"),
    [
        (1, 0), (2, 0),              # входят в базовый тариф
        (3, 80), (6, 80),            # ставка не падает, пока мало устройств
        (7, 70), (10, 70),
        (11, 60), (20, 60),
        (21, 50), (100, 50),
    ],
)
def test_marginal_rate_by_position(device_index: int, expected: int) -> None:
    assert monthly_rate(device_index) == Decimal(expected)


@pytest.mark.parametrize(
    ("devices", "expected"),
    [
        (2, 0),      # Solo, доплаты нет
        (3, 80),
        (4, 160),    # Duo
        (6, 320),    # Family
        (10, 600),   # Team
        (20, 1200),
    ],
)
def test_monthly_extra(devices: int, expected: int) -> None:
    assert monthly_extra_price(devices) == Decimal(expected)


@pytest.mark.parametrize(
    ("devices", "term_days", "expected_total"),
    [
        (4, 30, 360),    # Duo
        (6, 30, 520),    # Family
        (10, 30, 800),   # Team
        (4, 90, 972),
        (6, 180, 2496),
        (10, 365, 6720),
    ],
)
def test_formula_reproduces_preset_prices(
    devices: int, term_days: int, expected_total: int
) -> None:
    # Цена пресета = цена Solo на тот же срок плюс доплата за устройства.
    solo = {30: 200, 90: 540, 180: 960, 365: 1680}[term_days]
    total = solo + int(extra_devices_price(devices, term_days))

    # Допуск в десять рублей: в базе цены округлены до десятков.
    assert abs(total - expected_total) <= 10, (total, expected_total)


def test_mid_period_purchase_is_charged_for_remaining_days_only() -> None:
    full_month = extra_devices_price(3, term_days=30)
    three_weeks = extra_devices_price(3, term_days=30, days=21)

    assert full_month == Decimal(80)
    assert three_weeks == Decimal(56)


def test_annual_subscriber_keeps_his_discount_when_adding_mid_term() -> None:
    # Доплата в середине года считается по годовой ставке, а не по
    # месячной: иначе устройство посреди срока обошлось бы дороже, чем
    # то же устройство при продлении, и человек справедливо обиделся бы.
    mid_term = extra_devices_price(3, term_days=365, days=200)
    by_monthly_rate = extra_devices_price(3, term_days=30, days=200)

    assert mid_term < by_monthly_rate
    assert mid_term == Decimal(368)


def test_nothing_to_pay_for_the_base_plan() -> None:
    assert extra_devices_price(BASE_DEVICES, term_days=30) == Decimal(0)
    assert extra_devices_price(1, term_days=30) == Decimal(0)
    assert extra_devices_price(5, term_days=30, days=0) == Decimal(0)
