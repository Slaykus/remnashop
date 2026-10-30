"""
Админка кабинета: поиск клиента и карточка.

Главное здесь — что карточка показывается, даже когда панель не отвечает
(разбирать клиента нужно как раз тогда), что лимит устройств разложен на
тариф, докупку и подарок, и что наружу не уходят ссылка подписки и IP.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from remnapy.enums.users import TrafficLimitStrategy

from src.application.dto import PlanSnapshotDto, PriceDetailsDto, SubscriptionDto, UserDto
from src.core.enums import PlanType
from src.application.dto.admin_clients import AdminClientRow, AdminClientsPage
from src.web.endpoints.internal_admin import client_card, clients_page

card = client_card.__dishka_orig_func__
table = clients_page.__dishka_orig_func__

NOW = datetime.now(timezone.utc)
TG = 700000044
PAYMENT = uuid4()

TEAM = PlanSnapshotDto(
    id=5,
    name="Team",
    type=PlanType.DEVICES,
    traffic_limit=0,
    device_limit=10,
    duration=30,
    traffic_limit_strategy=TrafficLimitStrategy.NO_RESET,
)


def _user(uid=44, tg=TG, name="Клиент"):
    return UserDto(id=uid, telegram_id=tg, name=name, username="client")


def _sub():
    return SubscriptionDto(
        id=687,
        user_id=44,
        user_remna_id=uuid4(),
        traffic_limit=0,
        device_limit=15,
        extra_devices=0,
        traffic_limit_strategy=TrafficLimitStrategy.NO_RESET,
        expire_at=NOW + timedelta(days=16),
        url="https://secret.invalid/sub/KEY",
        plan_snapshot=TEAM,
    )


def _transaction():
    return SimpleNamespace(
        payment_id=PAYMENT,
        user_id=44,
        status="COMPLETED",
        purchase_type="RENEW",
        gateway_type="YOOKASSA",
        currency="RUB",
        pricing=PriceDetailsDto(
            original_amount=Decimal(800), discount_percent=50, final_amount=Decimal(400)
        ),
        plan_snapshot=TEAM,
        is_test=False,
        is_gift=False,
        created_at=NOW,
        updated_at=NOW,
    )


def _deps(panel_ok=True):
    user = _user()

    async def by_tg(tg):
        return user if tg == TG else None

    async def by_id(uid):
        return user if uid == 44 else None

    async def partial(q):
        return [user] if q.lower() in "клиент client" else []

    async def current(uid):
        return _sub()

    async def by_payment(pid):
        return _transaction() if pid == PAYMENT else None

    async def by_user(uid):
        return [_transaction()]

    async def referral(uid):
        return SimpleNamespace(referrer=_user(uid=7, tg=700000007, name="Друг"))

    async def count(uid):
        return 3

    async def partner(uid):
        return None

    async def devices(uuid):
        if not panel_ok:
            raise RuntimeError("panel down")
        return [
            SimpleNamespace(
                hwid="abc",
                platform="iOS",
                os_version="18",
                device_model="iPhone",
                request_ip="203.0.113.5",
                created_at=NOW,
                updated_at=NOW,
            )
        ]

    async def panel_user(uuid):
        if not panel_ok:
            raise RuntimeError("panel down")
        return SimpleNamespace(status="ACTIVE", used_traffic_bytes=1024.0, online_at=NOW)

    return dict(
        user_dao=SimpleNamespace(
            get_by_telegram_id=by_tg, get_by_id=by_id, get_by_partial_name=partial
        ),
        subscription_dao=SimpleNamespace(get_current=current),
        transaction_dao=SimpleNamespace(get_by_payment_id=by_payment, get_by_user=by_user),
        referral_dao=SimpleNamespace(get_by_referred_id=referral, get_referrals_count=count),
        partner_dao=SimpleNamespace(get_by_user_id=partner),
        remnawave=SimpleNamespace(get_devices=devices),
        sdk=SimpleNamespace(users=SimpleNamespace(get_user_by_uuid=panel_user)),
    )


def _table(captured: list):
    async def page(query):
        captured.append(query)
        row = AdminClientRow(
            user_id=44, telegram_id=TG, name="Клиент", username="client", created_at=NOW,
            is_blocked=False, is_bot_blocked=False, personal_discount=50,
            subscription_status="ACTIVE", is_trial=False, plan_id=5, plan_name="Team",
            expire_at=NOW, device_limit=15, paid_rub=Decimal("1575.00"), payments=5,
        )
        return AdminClientsPage(rows=[row], total=1, counts={"all": 1, "active": 1})

    async def plans():
        return [
            SimpleNamespace(id=5, name="Team", is_active=True, is_trial=False),
            SimpleNamespace(id=1, name="Free", is_active=True, is_trial=True),
        ]

    return dict(
        user_dao=SimpleNamespace(admin_clients_page=page),
        plan_dao=SimpleNamespace(get_all=plans),
    )


# --- таблица -------------------------------------------------------------


async def test_table_passes_filters_and_clamps_the_page() -> None:
    seen: list = []
    r = await table(
        **_table(seen), status="expiring", source="site", plan_id=5, sort="paid",
        q=" rs_700000044 ", extra_telegram_ids=[-2], page=0, per_page=500,
    )
    q = seen[0]
    assert (q.status, q.source, q.plan_id, q.sort) == ("expiring", "site", 5, "paid")
    assert (q.q, q.payment_id, q.extra_telegram_ids) == ("rs_700000044", None, (-2,))
    assert (q.page, q.per_page) == (1, 100) and (r.page, r.per_page) == (1, 100)
    assert r.rows[0].paid_rub == "1575.00"


async def test_table_recognises_a_payment_id() -> None:
    seen: list = []
    await table(**_table(seen), q=str(PAYMENT))
    assert seen[0].payment_id == PAYMENT and seen[0].q == ""


async def test_trial_plans_are_not_offered_as_a_filter() -> None:
    r = await table(**_table([]))
    assert [p.name for p in r.plans] == ["Team"]


# --- карточка ------------------------------------------------------------


async def test_card_splits_the_device_limit() -> None:
    c = await card(telegram_id=TG, **_deps())
    s = c.subscription
    assert (s.device_limit, s.plan_devices, s.extra_devices, s.gifted_devices) == (15, 10, 0, 5)
    assert c.referrer.name == "Друг" and c.invited_count == 3 and c.is_partner is False
    assert c.transactions[0].final_amount == "400" and c.transactions_total == 1
    assert c.devices[0].device_model == "iPhone" and c.panel.status == "ACTIVE"


async def test_card_survives_a_panel_outage() -> None:
    c = await card(telegram_id=TG, **_deps(panel_ok=False))
    assert c.subscription.plan_name == "Team"
    assert c.panel.error and c.devices is None and c.devices_error


async def test_card_does_not_leak_the_key_or_ips() -> None:
    dumped = (await card(telegram_id=TG, **_deps())).model_dump_json()
    assert "secret.invalid" not in dumped and "203.0.113.5" not in dumped


async def test_unknown_client_is_404() -> None:
    with pytest.raises(HTTPException) as e:
        await card(telegram_id=1, **_deps())
    assert e.value.status_code == 404


# --- разбор поиска в выборке --------------------------------------------


def _where(**kw) -> str:
    from sqlalchemy.dialects import postgresql

    from src.application.dto.admin_clients import AdminClientsQuery
    from src.infrastructure.database.dao.user import UserDaoImpl

    cond = UserDaoImpl._admin_search_condition(AdminClientsQuery(**kw))
    return str(cond.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))


def test_search_condition_understands_what_admins_paste() -> None:
    assert _where(q="rs_8908171865") == "users.telegram_id = 8908171865"
    assert _where(q="44") == "users.telegram_id = 44 OR users.id = 44"
    assert "ilike" in _where(q="@client").lower() and "client" in _where(q="@client")
    assert _where(q="c") == "false"  # одна буква не выгружает всю базу
    assert "IN (-2)" in _where(q="c", extra_telegram_ids=(-2,))
    assert "transactions.payment_id" in _where(payment_id=PAYMENT)
