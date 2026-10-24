"""
Перенос зависимых строк перед удалением аккаунта.

Почти все ссылки на пользователя стоят с каскадным удалением, и раньше
удаление виртуального аккаунта молча уносило его платежи. Проверяется,
какие запросы уходят в базу и в каком случае слияние отказывает до любых
изменений. Каждый запрос компилируется под PostgreSQL — так ловится
опечатка в колонке, которую иначе нашёл бы только прод.
"""

import pytest
from sqlalchemy.dialects import postgresql

from src.core.exceptions import AccountMergeConflictError
from src.infrastructure.database.dao.user import UserDaoImpl

FROM, TO = 876, 264  # виртуальный и настоящий аккаунт


def _sql(stmt) -> str:
    return str(stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))


class _Result:
    rowcount = 1


class _Session:
    """Отвечает на проверки по таблице и id, записывает изменения."""

    def __init__(self, *, partners: set[int] = frozenset(), referred: set[int] = frozenset()):
        self.partners = partners
        self.referred = referred
        self.writes: list[str] = []

    async def scalar(self, stmt):
        sql = _sql(stmt)
        if "FROM partners" in sql:
            return next((1 for uid in self.partners if f"user_id = {uid}" in sql), None)
        if "FROM referrals" in sql:
            return next((1 for uid in self.referred if f"referred_id = {uid}" in sql), None)
        raise AssertionError(f"unexpected read: {sql}")

    async def execute(self, stmt):
        self.writes.append(_sql(stmt))
        return _Result()


def _dao(session: _Session) -> UserDaoImpl:
    dao = UserDaoImpl.__new__(UserDaoImpl)
    dao.session = session  # type: ignore[attr-defined]
    return dao


def _touched(session: _Session, table: str) -> list[str]:
    return [w for w in session.writes if w.startswith(f"UPDATE {table} ")]


async def test_payments_move_to_the_real_account() -> None:
    session = _Session()
    await _dao(session).reassign_dependents(FROM, TO)

    [stmt] = _touched(session, "transactions")
    assert f"SET user_id={TO}" in stmt
    assert f"WHERE transactions.user_id = {FROM}" in stmt
    # payment_id — ключ сверки со шлюзом, его трогать нельзя.
    assert "payment_id" not in stmt


async def test_payment_change_time_survives_the_move() -> None:
    # По updated_at видно, кто погасил платёж — таймер или шлюз. Слияние
    # меняет владельца, а не платёж, и отметку затирать не должно.
    session = _Session()
    await _dao(session).reassign_dependents(FROM, TO)
    [stmt] = _touched(session, "transactions")
    assert "updated_at=transactions.updated_at" in stmt
    assert "now()" not in stmt


async def test_partner_attribution_is_kept() -> None:
    session = _Session()
    await _dao(session).reassign_dependents(FROM, TO)
    assert _touched(session, "partner_earnings")
    assert _touched(session, "promocode_activations")
    assert _touched(session, "referral_rewards")


async def test_two_partners_refuse_before_changing_anything() -> None:
    # Балансы двух партнёров молча не склеить. Отказ — до первой записи.
    session = _Session(partners={FROM, TO})
    with pytest.raises(AccountMergeConflictError):
        await _dao(session).reassign_dependents(FROM, TO)
    assert session.writes == []


async def test_lone_partner_moves_with_the_person() -> None:
    session = _Session(partners={FROM})
    await _dao(session).reassign_dependents(FROM, TO)
    assert _touched(session, "partners")


async def test_existing_referrer_of_the_real_account_wins() -> None:
    # Человека приводят один раз. Telegram-аккаунт старше — его пригласивший
    # пришёл первым и остаётся.
    session = _Session(referred={TO})
    await _dao(session).reassign_dependents(FROM, TO)
    assert not any(f"referred_id={TO}" in w.replace(" ", "") for w in _touched(session, "referrals"))


async def test_referrer_moves_when_the_real_account_has_none() -> None:
    session = _Session()
    await _dao(session).reassign_dependents(FROM, TO)
    assert any("referred_id" in w.split("WHERE")[0] for w in _touched(session, "referrals"))


async def test_the_two_accounts_never_become_self_referral() -> None:
    session = _Session()
    await _dao(session).reassign_dependents(FROM, TO)
    for stmt in _touched(session, "referrals"):
        # Связь двух аккаунтов одного человека не переносится.
        assert f"!= {TO}" in stmt


async def test_every_statement_is_valid_postgres() -> None:
    session = _Session(partners={FROM})
    await _dao(session).reassign_dependents(FROM, TO)
    assert len(session.writes) >= 8
    assert all(w.startswith("UPDATE ") for w in session.writes)
