"""
Порядок шагов при слиянии аккаунтов.

Здесь важны не сами значения, а последовательность: что записывается до
коммита, что после, и что не происходит вовсе, когда что-то сломалось.
Прежняя версия коммитила посреди слияния и стирала платежи удалением —
обе ошибки видны именно по порядку.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.core.exceptions import AccountMergeConflictError
from src.web.endpoints.internal import MigrateTelegramRequest, migrate_telegram

migrate = migrate_telegram.__dishka_orig_func__

OLD_TG, NEW_TG = -82, 700000001
VIRTUAL, REAL = 876, 264


class _Events(list):
    def mark(self, name: str) -> None:
        self.append(name)


def _subscription(user_id: int, traffic: int, devices: int, days: int, name: str):
    return SimpleNamespace(
        id=user_id * 10,
        user_id=user_id,
        user_remna_id=uuid4(),
        traffic_limit=traffic,
        device_limit=devices,
        extra_devices=0,
        traffic_limit_strategy="NO_RESET",
        tag=name,
        internal_squads=[],
        external_squad=None,
        is_trial=False,
        expire_at=datetime.now(timezone.utc) + timedelta(days=days),
        plan_snapshot=SimpleNamespace(name=name),
        status="LIMITED",
    )


def _deps(events: _Events, *, virtual_sub, real_sub, conflict=True, panel_fails=False,
          merge_conflict=False):
    users = {
        OLD_TG: SimpleNamespace(id=VIRTUAL, telegram_id=OLD_TG),
        NEW_TG: SimpleNamespace(id=REAL, telegram_id=NEW_TG) if conflict else None,
    }
    subs = {OLD_TG: virtual_sub, NEW_TG: real_sub}

    async def get_by_telegram_id(tg):
        return users.get(tg)

    async def reassign(frm, to):
        events.mark("reassign")
        if merge_conflict:
            raise AccountMergeConflictError("both partners")
        return {"transactions": 1}

    async def delete(uid):
        events.mark(f"delete:{uid}")
        return True

    async def update_user(**kw):
        events.mark("panel_update")
        if panel_fails:
            raise RuntimeError("panel down")
        return SimpleNamespace(status="ACTIVE")

    async def panel_delete(uuid):
        events.mark("panel_delete")

    class Uow:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, *a):
            if exc_type:
                events.mark("rollback")

        async def commit(self):
            events.mark("commit")

    async def noop(*a, **k):
        events.mark("noop")

    async def sub_update(s):
        events.mark("sub_update")

    async def move_sub(sid, uid):
        events.mark("move_sub")

    async def get_sub(tg):
        return subs.get(tg)

    return dict(
        user_dao=SimpleNamespace(
            get_by_telegram_id=get_by_telegram_id,
            reassign_dependents=reassign,
            delete=delete,
            set_current_subscription_by_id=noop,
            update=noop,
        ),
        ad_link_dao=SimpleNamespace(move_user=noop),
        subscription_dao=SimpleNamespace(
            get_current_by_telegram_id=get_sub, update=sub_update, move_to_user=move_sub
        ),
        remnawave=SimpleNamespace(update_user=update_user, rename_user=noop),
        sdk=SimpleNamespace(users=SimpleNamespace(delete_user=panel_delete)),
        uow=Uow(),
    )


def _call(deps):
    return migrate(old_telegram_id=OLD_TG, body=MigrateTelegramRequest(new_telegram_id=NEW_TG), **deps)


async def test_the_reported_case_moves_payments_and_takes_the_plan() -> None:
    events = _Events()
    virtual = _subscription(VIRTUAL, 0, 2, 180, "Solo")
    real = _subscription(REAL, 5, 1, 150, "IMPORTED")
    await _call(_deps(events, virtual_sub=virtual, real_sub=real))

    # Платежи переезжают до удаления, а удаление и всё прочее — в одном коммите.
    assert events.index("reassign") < events.index(f"delete:{VIRTUAL}") < events.index("commit")
    assert events.count("commit") == 1
    # Тариф Solo вместо пяти гигабайт — и в базе, и в панели.
    assert (real.traffic_limit, real.device_limit) == (0, 2)
    assert real.status.value == "ACTIVE"
    assert events.index("panel_update") < events.index("commit")
    # Лишний аккаунт в панели удаляется только после того, как база согласилась.
    assert events.index("commit") < events.index("panel_delete")


async def test_panel_failure_changes_nothing() -> None:
    events = _Events()
    virtual = _subscription(VIRTUAL, 0, 2, 180, "Solo")
    real = _subscription(REAL, 5, 1, 150, "IMPORTED")

    with pytest.raises(HTTPException) as err:
        await _call(_deps(events, virtual_sub=virtual, real_sub=real, panel_fails=True))

    assert err.value.status_code == 503
    assert "commit" not in events
    assert "rollback" in events
    # Ни удаления аккаунта, ни удаления в панели: лучше два аккаунта, чем
    # оплаченное, которое не работает.
    assert f"delete:{VIRTUAL}" not in events
    assert "panel_delete" not in events


async def test_two_partners_refuse_with_409_and_no_changes() -> None:
    events = _Events()
    virtual = _subscription(VIRTUAL, 0, 2, 30, "Solo")
    real = _subscription(REAL, 0, 2, 30, "Solo")

    with pytest.raises(HTTPException) as err:
        await _call(_deps(events, virtual_sub=virtual, real_sub=real, merge_conflict=True))

    assert err.value.status_code == 409
    assert "commit" not in events
    assert "panel_update" not in events


async def test_better_telegram_plan_is_kept_but_gets_the_days() -> None:
    events = _Events()
    virtual = _subscription(VIRTUAL, 0, 2, 30, "Solo")
    real = _subscription(REAL, 0, 4, 10, "Duo")
    real_end = real.expire_at

    await _call(_deps(events, virtual_sub=virtual, real_sub=real))

    assert (real.traffic_limit, real.device_limit, real.tag) == (0, 4, "Duo")
    assert real.expire_at - real_end >= timedelta(days=30)


async def test_subscription_moves_whole_when_telegram_has_none() -> None:
    # Ветка, которая работала верно, — только теперь и платежи с ней.
    events = _Events()
    virtual = _subscription(VIRTUAL, 0, 2, 30, "Solo")
    await _call(_deps(events, virtual_sub=virtual, real_sub=None))

    assert events.index("reassign") < events.index("move_sub") < events.index("commit")
    assert events.count("commit") == 1
    assert "panel_update" not in events
    assert "panel_delete" not in events


async def test_cabinet_account_without_subscription_still_keeps_payments() -> None:
    # Третья ветка: подписки в кабинете нет — например, купили подарок.
    # Платёж есть, и раньше он уходил вместе с аккаунтом.
    events = _Events()
    await _call(_deps(events, virtual_sub=None, real_sub=_subscription(REAL, 0, 2, 30, "Solo")))

    assert events.index("reassign") < events.index(f"delete:{VIRTUAL}") < events.index("commit")
    assert "panel_update" not in events
