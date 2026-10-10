"""
Кэш ссылок на оплату обязан протухать.

Кэш держит созданный платёж, чтобы повторное нажатие не плодило платежи
на стороне шлюза. Но ссылка у ЮKassa живёт минут десять-пятнадцать, а
запись жила столько же, сколько диалог: пока ключ в кэше, новый платёж не
создаётся. Человек, чья ссылка умерла, получал её же обратно сколько бы
раз ни возвращался в меню, — именно так и пришла жалоба.
"""

from datetime import timedelta

from src.core.utils.time import datetime_now
from src.telegram.routers.subscription.handlers import (
    _PAYMENT_CACHE_TTL,
    CachedPaymentData,
    _take_fresh_payment,
)

KEY = "RENEW:180:YOOKASSA"


def _entry(age: timedelta | None) -> CachedPaymentData:
    data = CachedPaymentData(
        payment_id="d3f1c0de-0000-0000-0000-000000000000",
        payment_url="https://yoomoney.ru/checkout/payments/v2/contract?orderId=x",
        final_pricing="{}",
        created_at="",
    )
    if age is None:
        # Запись из диалога, начатого до появления отметки времени.
        del data["created_at"]  # type: ignore[misc]
    else:
        data["created_at"] = (datetime_now() - age).isoformat()
    return data


def test_fresh_link_is_reused() -> None:
    # Двойное нажатие не должно создавать второй платёж.
    cache = {KEY: _entry(timedelta(seconds=30))}
    assert _take_fresh_payment(cache, KEY) is not None
    assert KEY in cache


def test_expired_link_is_dropped() -> None:
    # Та самая жалоба: ссылка создана полтора часа назад.
    cache = {KEY: _entry(timedelta(hours=1, minutes=39))}
    assert _take_fresh_payment(cache, KEY) is None
    # Выбросить обязательно: пока ключ в кэше, новый платёж не создаётся.
    assert KEY not in cache


def test_entry_without_timestamp_is_dropped() -> None:
    # Диалоги, уже застрявшие на мёртвой ссылке, должны расклиниться сами.
    cache = {KEY: _entry(None)}
    assert _take_fresh_payment(cache, KEY) is None
    assert KEY not in cache


def test_broken_timestamp_is_dropped() -> None:
    entry = _entry(timedelta(seconds=1))
    entry["created_at"] = "не дата"
    cache = {KEY: entry}
    assert _take_fresh_payment(cache, KEY) is None
    assert KEY not in cache


def test_missing_key_is_not_an_error() -> None:
    assert _take_fresh_payment({}, KEY) is None


def test_ttl_is_shorter_than_the_shortest_gateway_link() -> None:
    # Смысл срока в том, чтобы он кончался раньше самой ссылки. У ЮKassa
    # это около десяти минут; запас нужен на время между выдачей ссылки и
    # нажатием по ней.
    assert _PAYMENT_CACHE_TTL <= timedelta(minutes=5)
