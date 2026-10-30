"""
Платежи в админке кабинета: повторная выдача и сверка с ЮKassa.

Повтор — это деньги: он должен срабатывать только для оплаченного, но не
выданного платежа, и никогда для отменённого, тестового или подарочного.
Сверка должна находить три вида расхождений и не путать их.
"""

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.dialects import postgresql

from src.core.enums import PaymentGatewayType, TransactionStatus
from src.infrastructure.database.dao.transaction import TransactionDaoImpl
from src.web.endpoints.internal_admin import _reconcile, retry_payment

retry = retry_payment.__dishka_orig_func__
NOW = datetime.now(timezone.utc)


def _tx(status=TransactionStatus.FAILED, amount="400", test=False, gift=False, pid=None):
    return SimpleNamespace(
        payment_id=pid or uuid4(),
        user_id=44,
        status=status,
        is_test=test,
        is_gift=gift,
        gateway_type=PaymentGatewayType.YOOKASSA,
        pricing=SimpleNamespace(final_amount=Decimal(amount)),
    )


def _retry_deps(tx, *, fails=False):
    state = {"tx": tx, "calls": 0}

    async def by_pid(pid):
        return state["tx"]

    async def by_id(uid):
        return SimpleNamespace(telegram_id=700000044)

    async def process(dto):
        state["calls"] += 1
        if fails:
            raise RuntimeError("panel down")
        state["tx"] = SimpleNamespace(**{**vars(tx), "status": TransactionStatus.COMPLETED})

    deps = dict(
        transaction_dao=SimpleNamespace(get_by_payment_id=by_pid),
        user_dao=SimpleNamespace(get_by_id=by_id),
        process_payment=SimpleNamespace(system=process),
    )
    return deps, state


# --- повторная выдача --------------------------------------------------------


async def test_retry_delivers_a_paid_but_failed_payment() -> None:
    tx = _tx()
    deps, state = _retry_deps(tx)
    r = await retry(payment_id=tx.payment_id, **deps)
    assert (r.status_before, r.status_after, r.telegram_id) == ("FAILED", "COMPLETED", 700000044)
    assert state["calls"] == 1


@pytest.mark.parametrize(
    "tx",
    [
        _tx(status=TransactionStatus.CANCELED),  # не оплачен — выдавать нельзя
        _tx(status=TransactionStatus.PENDING),
        _tx(status=TransactionStatus.COMPLETED),  # уже выдан
        _tx(test=True),
        _tx(gift=True),
    ],
)
async def test_retry_refuses_anything_but_paid_and_undelivered(tx) -> None:
    deps, state = _retry_deps(tx)
    with pytest.raises(HTTPException) as e:
        await retry(payment_id=tx.payment_id, **deps)
    assert e.value.status_code == 400 and state["calls"] == 0


async def test_failed_retry_is_reported() -> None:
    tx = _tx()
    deps, _ = _retry_deps(tx, fails=True)
    with pytest.raises(HTTPException) as e:
        await retry(payment_id=tx.payment_id, **deps)
    assert e.value.status_code == 400 and "panel down" in e.value.detail


# --- сверка ------------------------------------------------------------------


async def test_reconcile_sorts_discrepancies() -> None:
    ok, failed, wrong_sum, lost = (str(uuid4()) for _ in range(4))
    ours = [
        _tx(TransactionStatus.COMPLETED, "400", pid=ok),
        _tx(TransactionStatus.FAILED, "400", pid=failed),
        _tx(TransactionStatus.COMPLETED, "200", pid=wrong_sum),
    ]

    async def by_ids(ids):
        return [t for t in ours if t.payment_id in {str(i) for i in ids}]

    async def by_id(uid):
        return SimpleNamespace(telegram_id=700000044)

    def yk(pid, amount="400.00", test=False):
        return {"id": pid, "created_at": "2026-10-30T10:00:00Z", "amount": amount,
                "currency": "RUB", "test": test, "description": "Team"}

    r = await _reconcile(
        [yk(ok), yk(failed), yk(wrong_sum), yk(lost), yk(str(uuid4()), test=True)],
        NOW,
        SimpleNamespace(get_by_payment_ids=by_ids),
        SimpleNamespace(get_by_id=by_id),
    )
    assert (r.yookassa_succeeded, r.test_skipped) == (4, 1)
    assert [i.payment_id for i in r.missing] == [lost]
    assert [(i.payment_id, i.our_status) for i in r.not_completed] == [(failed, "FAILED")]
    assert [(i.payment_id, i.amount, i.our_amount) for i in r.amount_mismatch] == [
        (wrong_sum, "400.00", "200")
    ]


# --- поиск по клиенту -----------------------------------------------------------


def _cond(q: str) -> str:
    c = TransactionDaoImpl._admin_client_condition(q)
    return str(c.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))


def test_payment_search_by_client() -> None:
    assert _cond("rs_431720831") == "users.telegram_id = 431720831"
    assert "ilike" in _cond("@client").lower()
    assert _cond("x") == "false"
