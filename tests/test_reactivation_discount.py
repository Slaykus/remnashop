"""
Письмо «скидка заканчивается завтра» не должно приходить без скидки.

08.09 трое получили его с цифрой 0%: кампания только запустилась и
застала их уже на пятом дне, предложения со скидкой они не получали, а
«последний зов» пришёл. Читается как насмешка, и починка в том, чтобы
такое письмо просто не отправлять.
"""

from datetime import datetime, timedelta, timezone

import pytest

from src.application.dto import UserDto
from src.application.services.pricing import PricingService
from src.application.use_cases.reactivation import REACTIVATION_STEPS


def _user(discount: int, expires_in_days: float | None) -> UserDto:
    expires_at = (
        datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        if expires_in_days is not None
        else None
    )
    return UserDto(
        name="test",
        purchase_discount=discount,
        purchase_discount_expires_at=expires_at,
    )


@pytest.mark.parametrize(
    ("discount", "expires_in_days", "expected"),
    [
        (20, 1, 20),      # жива
        (20, -1, 0),      # сгорела — именно этот случай и ловим
        (20, None, 20),   # бессрочная, как было до кампании
        (0, 1, 0),
    ],
)
def test_effective_discount_respects_expiry(
    discount: int, expires_in_days: float | None, expected: int
) -> None:
    assert PricingService().get_effective_discount(_user(discount, expires_in_days)) == expected


def test_every_letter_naming_a_discount_is_marked() -> None:
    # Отмечены должны быть все четыре письма про скидку и только они:
    # напоминания про неактивированный пробник скидку не называют.
    marked = {step.kind for step in REACTIVATION_STEPS if step.quotes_discount}
    assert marked == {
        "TRIAL_EXPIRED_D3",
        "TRIAL_EXPIRED_D5",
        "PAID_EXPIRED_D3",
        "PAID_EXPIRED_D5",
    }


def test_last_call_letters_grant_nothing() -> None:
    # Проверка пропуска стоит только на письмах без своей выдачи —
    # у выдающих скидка появится прямо сейчас, и ноля там быть не может.
    last_calls = [s for s in REACTIVATION_STEPS if s.kind.endswith("_D5")]
    assert last_calls
    assert all(step.grant == 0 for step in last_calls)
