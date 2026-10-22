"""
Ручная правка лимита устройств и счётчик докупленных.

Админка писала только потолок. Опустив лимит, владелец убирал устройство,
но счётчик докупленных оставался — и при продлении устройство возвращалось,
а его стоимость снова попадала в цену. Клиент, попросивший устройство
убрать и получивший возврат, заплатил бы за него второй раз.

Правило намеренно несимметричное: счётчик только уменьшаем. Поднятый
вручную лимит — подарок, и молча делать его платным нельзя.
"""

import pytest

from src.application.use_cases.subscription.commands.management import (
    extras_after_limit_change,
)

SOLO = 2  # сколько устройств даёт тариф Solo


def test_lowering_the_limit_drops_the_paid_counter() -> None:
    # Тот самый случай: Solo + 1 докупленное, владелец вернул лимит к двум.
    assert extras_after_limit_change(plan_devices=SOLO, new_limit=2, current_extras=1) == 0


def test_lowering_partway_keeps_what_still_fits() -> None:
    # Было два докупленных (лимит 4), сняли одно — одно и осталось платным.
    assert extras_after_limit_change(plan_devices=SOLO, new_limit=3, current_extras=2) == 1


def test_raising_the_limit_does_not_create_paid_devices() -> None:
    # Подарок остаётся подарком: счётчик не растёт, и в цену продления
    # эти устройства не попадают.
    assert extras_after_limit_change(plan_devices=SOLO, new_limit=8, current_extras=0) == 0


def test_raising_above_paid_leaves_the_paid_count_alone() -> None:
    # Одно оплачено, сверху подарили ещё — платным остаётся одно.
    assert extras_after_limit_change(plan_devices=SOLO, new_limit=10, current_extras=1) == 1


def test_limit_below_the_plan_zeroes_the_counter() -> None:
    # Ниже тарифного потолка докупленных быть не может по определению.
    assert extras_after_limit_change(plan_devices=SOLO, new_limit=1, current_extras=2) == 0


def test_unlimited_plan_has_no_extras() -> None:
    # Безлимит задан нулём. Ненулевой счётчик при продлении превратил бы
    # его в 0 + extras, то есть в пару устройств вместо безлимита.
    assert extras_after_limit_change(plan_devices=0, new_limit=5, current_extras=3) == 0


@pytest.mark.parametrize("new_limit", range(0, 13))
@pytest.mark.parametrize("current_extras", range(0, 5))
def test_result_is_never_more_than_before(new_limit: int, current_extras: int) -> None:
    # Главный инвариант: правка лимита не может добавить платных устройств.
    result = extras_after_limit_change(
        plan_devices=SOLO, new_limit=new_limit, current_extras=current_extras
    )
    assert 0 <= result <= current_extras


@pytest.mark.parametrize("new_limit", range(1, 13))
@pytest.mark.parametrize("current_extras", range(0, 5))
def test_renewal_never_exceeds_the_set_limit(new_limit: int, current_extras: int) -> None:
    # Продление считает plan + extras. Эта сумма не должна оказаться выше
    # того, что владелец выставил руками, — иначе лимит «отрастал» бы назад.
    extras = extras_after_limit_change(
        plan_devices=SOLO, new_limit=new_limit, current_extras=current_extras
    )
    assert SOLO + extras <= max(SOLO, new_limit)
