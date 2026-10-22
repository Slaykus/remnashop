"""
Провал создания платежа в кабинете должен быть слышен.

Раньше эндпоинт отдавал 502 и больше ничего: ни строки в логе, ни слова
владельцу. А платёж на стороне шлюза к тому моменту уже создан — он
создаётся внутри той же транзакции БД, что и наша запись, — поэтому
несохранившаяся запись оставляет у шлюза платёж, о котором мы не знаем.
Один такой нашёлся 22.10.2026: мы узнали о нём только из его же вебхука
об отмене, час спустя.

Главное, что проверяется здесь: сообщить о провале нельзя ценой нового
провала. Если канал уведомлений недоступен, запрос обязан дойти до своего
502, а не упасть по другой причине.
"""

from types import SimpleNamespace

import pytest

from src.web.endpoints.internal import _report_payment_failure

BUILD = {
    "has_build": True,
    "time": "2026-10-22T08:00:00",
    "branch": "main",
    "tag": "v1",
    "commit_url": "https://example.invalid/c",
    "commit": "deadbee",
}
USER = SimpleNamespace(log="[USER:1:rs_1 (tester)]")
CONFIG = SimpleNamespace(build=SimpleNamespace(data=BUILD))


class _Publisher:
    def __init__(self) -> None:
        self.published: list = []

    async def publish(self, event) -> None:
        self.published.append(event)


class _BrokenPublisher:
    async def publish(self, event) -> None:
        raise RuntimeError("шина уведомлений недоступна")


async def test_failure_is_reported_to_the_owner() -> None:
    publisher = _Publisher()
    error = ValueError("база отказала на коммите")

    await _report_payment_failure(
        error,
        what="Web payment creation",
        user=USER,
        event_publisher=publisher,
        config=CONFIG,
    )

    assert len(publisher.published) == 1
    assert publisher.published[0].exception is error


async def test_broken_notification_does_not_mask_the_payment_error() -> None:
    # Если бы это пробрасывалось, вместо честного 502 про платёж кабинет
    # получил бы ошибку про уведомления, и причина потерялась бы снова.
    await _report_payment_failure(
        ValueError("база отказала на коммите"),
        what="Web payment creation",
        user=USER,
        event_publisher=_BrokenPublisher(),
        config=CONFIG,
    )


async def test_reporting_never_swallows_by_returning_a_value() -> None:
    # Помощник только сообщает: решение, что отдать клиенту, остаётся за
    # эндпоинтом, и подменить его помощник не может.
    publisher = _Publisher()
    result = await _report_payment_failure(
        ValueError("x"),
        what="Web payment creation",
        user=USER,
        event_publisher=publisher,
        config=CONFIG,
    )
    assert result is None


@pytest.mark.parametrize("what", ["Web payment creation", "Web device payment creation"])
async def test_both_payment_paths_can_report(what: str) -> None:
    # Обычная покупка и докупка устройства ходят через один помощник —
    # вторая раньше тоже молчала.
    publisher = _Publisher()
    await _report_payment_failure(
        ValueError("x"), what=what, user=USER, event_publisher=publisher, config=CONFIG
    )
    assert len(publisher.published) == 1
