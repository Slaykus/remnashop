"""
Действия админки кабинета: лимит устройств «в подарок» или «платно»,
удаление устройств, тариф без оплаты.

Главное — деньги: «платно» действительно попадает в цену продления, а
«подарок» нет; и админ, удаляя устройства, не сжигает клиенту его
собственный сброс и не упирается в клиентское ограничение по частоте.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from remnapy.enums.users import TrafficLimitStrategy

from src.application.dto import PlanSnapshotDto, SubscriptionDto, UserDto
from src.application.services.device_pricing import gifted_devices
from src.application.use_cases.remnawave.commands.management import (
    AdminDeleteDevices,
    AdminDeleteDevicesDto,
)
from src.application.use_cases.subscription.commands.management import (
    UpdateDeviceLimit,
    UpdateDeviceLimitDto,
)
from src.core.enums import PlanType
from src.web.endpoints.internal_admin import (
    AdminDeviceLimitRequest,
    AdminSetPlanRequest,
    set_device_limit,
    set_plan,
)

NOW = datetime.now(timezone.utc)
TEAM = PlanSnapshotDto(
    id=5, name="Team", type=PlanType.DEVICES, traffic_limit=0, device_limit=10,
    duration=30, traffic_limit_strategy=TrafficLimitStrategy.NO_RESET,
)


def _sub(devices=10, extra=0):
    return SubscriptionDto(
        id=1, user_id=44, user_remna_id=uuid4(), traffic_limit=0, device_limit=devices,
        extra_devices=extra, traffic_limit_strategy=TrafficLimitStrategy.NO_RESET,
        expire_at=NOW + timedelta(days=16), url="https://x.invalid", plan_snapshot=TEAM,
    )


class Uow:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def commit(self):
        pass


def _limit_uc(sub):
    panel = {}

    async def get_by_id(uid):
        return UserDto(id=44, telegram_id=700000044, name="c")

    async def current(uid):
        return sub

    async def noop(*a, **k):
        return None

    async def update_user(**kw):
        panel["limit"] = kw["subscription"].device_limit

    uc = UpdateDeviceLimit.__new__(UpdateDeviceLimit)
    uc.uow = Uow()
    uc.user_dao = SimpleNamespace(get_by_id=get_by_id)
    uc.subscription_dao = SimpleNamespace(get_current=current, update=noop)
    uc.remnawave = SimpleNamespace(update_user=update_user)
    return uc, panel


# --- лимит устройств -------------------------------------------------------


async def test_gift_is_free_and_survives_renewal() -> None:
    sub = _sub()
    uc, panel = _limit_uc(sub)
    await uc._execute(SimpleNamespace(log="[a]"), UpdateDeviceLimitDto(44, 15))
    assert (sub.device_limit, sub.extra_devices, gifted_devices(sub), panel["limit"]) == (15, 0, 5, 15)


async def test_paid_goes_into_the_renewal_price() -> None:
    sub = _sub()
    uc, _ = _limit_uc(sub)
    await uc._execute(SimpleNamespace(log="[a]"), UpdateDeviceLimitDto(44, 15, paid=True))
    assert (sub.device_limit, sub.extra_devices, gifted_devices(sub)) == (15, 5, 0)


async def test_paid_turns_an_earlier_gift_into_paid() -> None:
    sub = _sub(devices=15)  # 5 подарено
    uc, _ = _limit_uc(sub)
    await uc._execute(SimpleNamespace(log="[a]"), UpdateDeviceLimitDto(44, 15, paid=True))
    assert (sub.extra_devices, gifted_devices(sub)) == (5, 0)


async def test_lowering_below_the_plan_clears_paid_devices_either_way() -> None:
    for paid in (False, True):
        sub = _sub(devices=12, extra=2)
        uc, _ = _limit_uc(sub)
        await uc._execute(SimpleNamespace(log="[a]"), UpdateDeviceLimitDto(44, 8, paid=paid))
        assert (sub.device_limit, sub.extra_devices) == (8, 0)


# --- удаление устройств ------------------------------------------------------


async def test_admin_device_reset_does_not_burn_the_clients_own_reset() -> None:
    sub = _sub()
    calls = []

    async def current(uid):
        return sub

    async def rec(name, *a):
        calls.append(name)

    uc = AdminDeleteDevices.__new__(AdminDeleteDevices)
    uc.subscription_dao = SimpleNamespace(get_current=current)
    uc.remnawave = SimpleNamespace(
        delete_device=lambda *a: rec("one", *a),
        delete_all_devices=lambda *a: rec("all", *a),
        drop_connections=lambda *a: rec("drop", *a),
    )
    await uc._execute(SimpleNamespace(log="[a]"), AdminDeleteDevicesDto(44, hwid="abc"))
    await uc._execute(SimpleNamespace(log="[a]"), AdminDeleteDevicesDto(44))
    assert calls == ["one", "drop", "all", "drop"]
    assert sub.device_single_reset_at is None and sub.device_all_reset_at is None


# --- проверки на входе -------------------------------------------------------


def _endpoint_deps(sub):
    async def by_tg(tg):
        return UserDto(id=44, telegram_id=tg, name="c")

    async def current(uid):
        return sub

    async def run(dto):
        raise AssertionError("не должно было дойти до сценария")

    return dict(
        user_dao=SimpleNamespace(get_by_telegram_id=by_tg),
        subscription_dao=SimpleNamespace(get_current=current),
    ), SimpleNamespace(system=run)


@pytest.mark.parametrize("limit", [0, -1, 101])
async def test_device_limit_out_of_range_is_refused(limit) -> None:
    deps, uc = _endpoint_deps(_sub())
    with pytest.raises(HTTPException) as e:
        await set_device_limit.__dishka_orig_func__(
            telegram_id=1, body=AdminDeviceLimitRequest(device_limit=limit), update_device_limit=uc, **deps
        )
    assert e.value.status_code == 400


async def test_plan_keeps_the_current_term_when_days_are_not_given() -> None:
    sub = _sub()
    seen = []

    async def run(dto):
        seen.append(dto)

    deps, _ = _endpoint_deps(sub)
    await set_plan.__dishka_orig_func__(
        telegram_id=1, body=AdminSetPlanRequest(plan_id=3), set_subscription=SimpleNamespace(system=run), **deps
    )
    assert (seen[0].plan_id, seen[0].duration) == (3, 16)


async def test_plan_without_a_subscription_needs_days() -> None:
    deps, uc = _endpoint_deps(None)
    with pytest.raises(HTTPException) as e:
        await set_plan.__dishka_orig_func__(
            telegram_id=1, body=AdminSetPlanRequest(plan_id=3), set_subscription=uc, **deps
        )
    assert e.value.status_code == 400
