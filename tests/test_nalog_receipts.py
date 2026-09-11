"""Описание чека «Мой налог».

Чек — официальный документ, и его текст читает живой человек. В сентябре
туда уехало `Подписка Rain — ('Solo', {})`: название тарифа лежит в
событии в форме для переводов, а в строку чека попадало как есть.
"""

import pytest

from src.application.services.nalog_receipts import receipt_description


@pytest.mark.parametrize(
    "plan_name",
    [
        ("Solo", {}),
        ["Solo", {}],
        "Solo",
        " Solo ",
    ],
)
def test_plan_name_renders_as_plain_text(plan_name: object) -> None:
    assert receipt_description(plan_name) == "Подписка Rain — Solo"


def test_no_brackets_leak_into_receipt() -> None:
    description = receipt_description(("Duo", {"value": 1}))

    assert description == "Подписка Rain — Duo"
    assert "(" not in description
    assert "{" not in description


def test_empty_value_does_not_break_sending() -> None:
    # Пустое значение — повод для скучного чека, но не для падения отправки:
    # деньги уже получены, чек обязан уйти.
    assert receipt_description(()) == "Подписка Rain — "
    assert receipt_description(None) == "Подписка Rain — "
