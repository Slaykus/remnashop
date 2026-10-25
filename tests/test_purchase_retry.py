"""
Платёж прошёл, а выдача подписки упала — бот допроводит его сам.

25.10.2026 панель один раз не ответила на продление Family: деньги списаны,
подписка не выдана, транзакция осталась в FAILED, и узнали об этом из
обращения клиента. Повтор был предусмотрен — переход FAILED -> COMPLETED
разрешён, — но его никто не запускал.

Здесь проверяется не сама выдача, а поведение вокруг неё: о первом сбое
владелец узнаёт и видит, до какого часа ждать; повторные сбои молчат, иначе
каждые десять минут прилетало бы новое сообщение; удачный повтор отдельно
сообщает, что всё выдано, — иначе владелец вернёт деньги за уже выданное.
"""

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

from src.application.dto import PlanSnapshotDto, PriceDetailsDto, TransactionDto, UserDto
from src.application.use_cases.gateways.commands.payment import (
    PURCHASE_RETRY_EVERY_MINUTES,
    PURCHASE_RETRY_WINDOW,
    ProcessPayment,
)
from src.application.use_cases.gateways.commands.retry import RetryFailedPurchases
from src.core.enums import Currency, PaymentGatewayType, PurchaseType, TransactionStatus
from src.infrastructure.services.remnawave import RemnawaveImpl

ROOT = Path(__file__).resolve().parent.parent


def _transaction(prior: TransactionStatus) -> TransactionDto:
    return TransactionDto(
        id=576,
        payment_id=uuid4(),
        user_id=55,
        status=prior,
        purchase_type=PurchaseType.RENEW,
        gateway_type=PaymentGatewayType.YOOKASSA,
        pricing=PriceDetailsDto.test(),
        currency=Currency.RUB,
        plan_snapshot=PlanSnapshotDto.test(),
        created_at=datetime(2026, 10, 25, 11, 19, tzinfo=timezone.utc),
    )


class _Uow:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def commit(self):
        pass


def _process_payment(*, panel_fails: bool, events: list) -> ProcessPayment:
    async def purchase(dto):
        if panel_fails:
            raise httpx.ConnectTimeout("panel down")
        events.append("delivered")

    async def notify_system(payload, **kw):
        events.append(f"notify:{payload.i18n_key}:{payload.i18n_kwargs.get('retry_until', '')}")

    async def redirect_failed(tid):
        events.append("redirect:failed")

    async def update_status(pid, status):
        events.append(f"status:{status}")

    async def nothing(*a, **k):
        return None

    pp = ProcessPayment.__new__(ProcessPayment)
    pp.uow = _Uow()
    pp.purchase_subscription = SimpleNamespace(system=purchase)
    pp.transaction_dao = SimpleNamespace(update_status=update_status)
    pp.subscription_dao = SimpleNamespace(get_current=nothing)
    pp.notifier = SimpleNamespace(notify_system=notify_system, notify_admins=nothing, notify_user=nothing)
    pp.redirect = SimpleNamespace(
        to_failed_payment=redirect_failed, to_success_payment=nothing, to_devices=nothing
    )
    pp.event_publisher = SimpleNamespace(publish=nothing)
    pp.assign_referral_rewards = SimpleNamespace(system=nothing)
    pp._accrue_partner_share = nothing  # type: ignore[method-assign]
    return pp


USER = UserDto(id=55, telegram_id=700000001, name="<$--ILYA--$>")


async def test_first_failure_tells_the_owner_until_when_to_wait() -> None:
    events: list = []
    pp = _process_payment(panel_fails=True, events=events)

    with pytest.raises(Exception):
        await pp._handle_success(USER, _transaction(TransactionStatus.PENDING))

    assert "status:FAILED" in events
    assert "redirect:failed" in events
    [notice] = [e for e in events if e.startswith("notify:")]
    # Новое сообщение с крайним сроком, а не «требуется ручная проверка».
    assert notice.startswith("notify:event-payment-purchase-retrying:")
    # 11:19 UTC + 6 ч = 17:19 UTC = 20:19 МСК.
    assert notice.endswith("25.10 20:19")


async def test_repeated_failure_is_silent() -> None:
    events: list = []
    pp = _process_payment(panel_fails=True, events=events)

    with pytest.raises(Exception):
        await pp._handle_success(USER, _transaction(TransactionStatus.FAILED))

    assert "status:FAILED" in events
    assert not [e for e in events if e.startswith("notify:")]
    assert "redirect:failed" not in events


async def test_recovered_retry_says_so() -> None:
    events: list = []
    pp = _process_payment(panel_fails=False, events=events)

    await pp._handle_success(USER, _transaction(TransactionStatus.FAILED))

    assert "delivered" in events
    assert "notify:event-payment-purchase-recovered:" in events


async def test_ordinary_success_sends_no_recovery_notice() -> None:
    events: list = []
    pp = _process_payment(panel_fails=False, events=events)

    await pp._handle_success(USER, _transaction(TransactionStatus.PENDING))

    assert not [e for e in events if "recovered" in e]


def test_names_are_escaped_for_telegram_html() -> None:
    # Ники вроде <$--ILYA--$> ломали разбор HTML в сообщении.
    kwargs = ProcessPayment._payment_alert_kwargs(USER, _transaction(TransactionStatus.PENDING))
    assert "<" not in kwargs["name"]


async def test_retry_job_keeps_going_past_a_stuck_payment() -> None:
    stuck, fine = _transaction(TransactionStatus.FAILED), _transaction(TransactionStatus.FAILED)
    seen: list = []

    async def failed_since(since):
        assert datetime.now(timezone.utc) - since >= PURCHASE_RETRY_WINDOW - timedelta(seconds=5)
        return [stuck, fine]

    async def process(dto):
        seen.append(dto.payment_id)
        assert dto.new_transaction_status == TransactionStatus.COMPLETED
        if dto.payment_id == stuck.payment_id:
            raise RuntimeError("still down")

    job = RetryFailedPurchases(
        transaction_dao=SimpleNamespace(get_failed_purchases_since=failed_since),
        process_payment=SimpleNamespace(system=process),  # type: ignore[arg-type]
    )
    # Падение задачи — это ещё одно сообщение владельцу; она падать не должна.
    assert await job._execute(None, None) == 2  # type: ignore[arg-type]
    assert seen == [stuck.payment_id, fine.payment_id]


def test_schedule_matches_the_interval_named_to_the_owner() -> None:
    src = (ROOT / "src/infrastructure/taskiq/tasks/payments.py").read_text(encoding="utf-8")
    block = src[: src.index("async def retry_failed_purchases_task")]
    cron = re.findall(r'"cron": "\*/(\d+) \* \* \* \*"', block)[-1]
    assert int(cron) == PURCHASE_RETRY_EVERY_MINUTES


class TestPanelConnectRetry:
    """Соединение не установилось — запрос до панели не дошёл, повтор безопасен."""

    def _impl(self) -> RemnawaveImpl:
        impl = RemnawaveImpl.__new__(RemnawaveImpl)
        impl._CONNECT_RETRY_DELAYS = (0.0, 0.0)  # type: ignore[misc]
        return impl

    async def test_transient_connect_failure_is_retried(self) -> None:
        calls = []

        async def call():
            calls.append(1)
            if len(calls) < 3:
                raise httpx.ConnectTimeout("blip")
            return "ok"

        assert await self._impl()._with_connect_retry("update_user", call) == "ok"
        assert len(calls) == 3

    async def test_gives_up_after_the_last_attempt(self) -> None:
        async def call():
            raise httpx.ConnectError("down")

        with pytest.raises(httpx.ConnectError):
            await self._impl()._with_connect_retry("update_user", call)

    async def test_read_timeout_is_not_retried(self) -> None:
        # Тут запрос мог дойти и примениться — повторять вслепую нельзя.
        calls = []

        async def call():
            calls.append(1)
            raise httpx.ReadTimeout("slow")

        with pytest.raises(httpx.ReadTimeout):
            await self._impl()._with_connect_retry("create_user", call)
        assert len(calls) == 1
