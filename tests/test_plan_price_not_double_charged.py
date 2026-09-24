"""
Устройства тарифа не оплачиваются второй раз.

Цены пресетов пересчитаны по формуле и уже включают устройства, которые
тариф даёт. Надбавка сверху существует только ради докупленных. Когда её
считали от общего числа устройств, Duo с его четырьмя уходил в кассу как
«цена тарифа плюс ещё два устройства»: 360 вместо 360 и 520 на экране.

Тест держит границу между этими двумя величинами, потому что обе
называются «доплатой за устройства» и перепутать их легко.
"""

import pytest

from src.application.services.device_pricing import (
    BASE_DEVICES,
    bought_devices_price,
    extra_devices_price,
)

# Тариф и сколько устройств он даёт.
PLANS = [("Solo", 2), ("Duo", 4), ("уникальный 1707", 6), ("Family", 10)]


@pytest.mark.parametrize(("name", "plan_devices"), PLANS)
def test_plain_purchase_adds_nothing(name: str, plan_devices: int) -> None:
    # Покупка и смена тарифа: докупленных нет, значит и доплаты нет.
    for term in (30, 90, 180, 365):
        assert bought_devices_price(plan_devices, 0, term) == 0, name


@pytest.mark.parametrize(("name", "plan_devices"), PLANS)
def test_only_the_bought_ones_are_charged(name: str, plan_devices: int) -> None:
    # Доплата за одно докупленное равна разнице между «тариф плюс одно» и
    # «тариф», а не полной цене всех устройств сверх базовых.
    expected = extra_devices_price(plan_devices + 1, 30) - extra_devices_price(
        plan_devices, 30
    )
    assert bought_devices_price(plan_devices, 1, 30) == expected, name


def test_the_regression_itself() -> None:
    # Ровно тот случай, который попал в прод: Duo даёт четыре устройства,
    # и надбавка за них — ноль, а не цена двух сверх базовых.
    assert extra_devices_price(4, 30) == 160  # столько ошибочно добавлялось
    assert bought_devices_price(4, 0, 30) == 0


def test_unlimited_plan_has_nothing_to_add() -> None:
    # Безлимит задан нулём, а не числом: считать «сверх тарифа» не от чего.
    assert bought_devices_price(0, 3, 30) == 0


def test_base_plan_matches_the_old_meaning() -> None:
    # На тарифе ровно с базовым числом устройств обе величины совпадают —
    # отсюда и взялась путаница: на Solo ошибка не проявлялась.
    for extra in range(1, 5):
        assert bought_devices_price(BASE_DEVICES, extra, 30) == extra_devices_price(
            BASE_DEVICES + extra, 30
        )
