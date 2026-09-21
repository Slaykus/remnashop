"""
Докупка устройств не должна воровать время.

Ветка проведения поднимает потолок устройств и не трогает ни срок, ни
трафик — в отличие от смены тарифа, которая пересоздаёт подписку с нуля.
Здесь проверяется арифметика надбавки: сколько устройств записать сверх
тарифа, чтобы она пережила продление и попала в его цену.
"""

import pytest


def extra_after_purchase(plan_devices: int, purchased_total: int) -> int:
    """То же, что считает ветка DEVICES в PurchaseSubscription."""
    return max(0, purchased_total - plan_devices)


@pytest.mark.parametrize(
    ("plan_devices", "purchased_total", "expected_extra"),
    [
        (2, 3, 1),    # Solo плюс одно
        (2, 4, 2),    # Solo плюс два — столько же устройств, сколько у Duo
        (4, 6, 2),    # Duo плюс два
        (2, 10, 8),   # потолок докупки
        (2, 2, 0),    # ничего не докупили
    ],
)
def test_extra_is_the_gap_above_the_plan(
    plan_devices: int, purchased_total: int, expected_extra: int
) -> None:
    assert extra_after_purchase(plan_devices, purchased_total) == expected_extra


def test_extra_never_goes_negative() -> None:
    # Тариф мог подорожать устройствами уже после докупки: тогда надбавки
    # просто нет, но и отнимать у человека ничего нельзя.
    assert extra_after_purchase(plan_devices=6, purchased_total=4) == 0
