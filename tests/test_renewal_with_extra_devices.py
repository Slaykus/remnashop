"""
Продление с докупленными устройствами.

Дыра, ради которой всё это: надбавка переживала продление, но в его цену
не входила. Человек платил за третье устройство один раз и пользовался
им бесконечно, продлевая Solo за двести рублей.

Здесь проверяется и обратное — что обычная покупка без докупленных
устройств считается ровно как раньше.
"""

from decimal import Decimal

import pytest

from src.application.dto import PlanDurationDto, PlanPriceDto, UserDto
from src.application.services.pricing import PricingService
from src.core.enums import Currency


def _duration(days: int, rub: int) -> PlanDurationDto:
    return PlanDurationDto(
        days=days,
        prices=[PlanPriceDto(currency=Currency.RUB, price=Decimal(rub))],
    )


def _user(personal: int = 0) -> UserDto:
    return UserDto(name="test", personal_discount=personal)


@pytest.mark.parametrize(
    ("plan_rub", "surcharge", "discount", "expected"),
    [
        (200, 0, 0, 200),      # Solo без докупленных — как было
        (200, 80, 0, 280),     # Solo плюс одно устройство
        (200, 160, 0, 360),    # Solo плюс два — столько же, сколько Duo
        (200, 80, 95, 14),     # скидка считается от суммы, а не от тарифа
        (200, 0, 95, 10),
    ],
)
def test_surcharge_is_added_before_the_discount(
    plan_rub: int, surcharge: int, discount: int, expected: int
) -> None:
    price = PricingService().calculate_for_duration(
        _user(discount),
        _duration(30, plan_rub),
        Currency.RUB,
        extra_amount=Decimal(surcharge),
    )
    assert price.final_amount == Decimal(expected)


def test_plain_purchase_is_untouched() -> None:
    # Без надбавки вызов обязан дать то же, что и раньше: этот путь
    # проходят все покупки, и сломать его дороже всего.
    service = PricingService()
    duration = _duration(90, 540)

    with_default = service.calculate_for_duration(_user(), duration, Currency.RUB)
    with_zero = service.calculate_for_duration(
        _user(), duration, Currency.RUB, extra_amount=Decimal(0)
    )

    assert with_default.final_amount == with_zero.final_amount == Decimal(540)
    assert with_default.original_amount == Decimal(540)
