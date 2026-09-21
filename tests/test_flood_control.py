"""
Расписание исходящих запросов к телеграму.

21.09 бот лёг на четырнадцать минут, потому что не умел притормаживать.
Здесь проверяется, что теперь умеет: темп держится в рамках лимитов, а
на прямую просьбу подождать расписание сдвигается для всех.
"""

import asyncio

import pytest

from src.telegram.flood_control import (
    _GLOBAL_PER_SECOND,
    _PER_CHAT_INTERVAL,
    FloodControlMiddleware,
)


class SendMessage:
    def __init__(self, chat_id: int) -> None:
        self.chat_id = chat_id


class DeleteMessage:
    def __init__(self, chat_id: int) -> None:
        self.chat_id = chat_id


def test_only_sending_is_limited_per_chat() -> None:
    # Удаление под лимит «одно сообщение в секунду» не попадает: иначе
    # перерисовка экрана стоила бы человеку двух секунд вместо одной.
    middleware = FloodControlMiddleware()
    assert middleware._chat_key(SendMessage(42)) == 42
    assert middleware._chat_key(DeleteMessage(42)) is None


async def test_same_chat_is_spaced_out() -> None:
    middleware = FloodControlMiddleware()
    first = await middleware._reserve(42)
    second = await middleware._reserve(42)
    third = await middleware._reserve(42)

    assert first == 0.0
    assert second >= _PER_CHAT_INTERVAL * 0.99
    assert third >= second + _PER_CHAT_INTERVAL * 0.99


async def test_different_chats_do_not_wait_for_each_other() -> None:
    middleware = FloodControlMiddleware()
    delays = [await middleware._reserve(chat) for chat in range(10)]

    # Разные люди не стоят в очереди друг за другом — их разводит только
    # общий лимит на бота, а он куда просторнее.
    assert max(delays) < _PER_CHAT_INTERVAL


async def test_global_rate_is_respected() -> None:
    middleware = FloodControlMiddleware()
    count = 50
    delays = [await middleware._reserve(chat) for chat in range(count)]

    expected = (count - 1) / _GLOBAL_PER_SECOND
    assert delays[-1] == pytest.approx(expected, rel=0.05)


async def test_retry_after_pushes_everyone_back() -> None:
    middleware = FloodControlMiddleware()
    await middleware._reserve(1)
    middleware._push_back(1, delay=5.0)

    # Отказ по одному чату означает, что темп не понравился телеграму в
    # целом, поэтому подождать должны все.
    assert await middleware._reserve(2) >= 4.5
    assert await middleware._reserve(1) >= 4.5


async def test_waiting_never_blocks_the_lock() -> None:
    # Ожидание своей очереди происходит снаружи блокировки: иначе очередь
    # в один чат останавливала бы весь бот.
    middleware = FloodControlMiddleware()
    await middleware._reserve(1)

    async def reserve_other() -> float:
        return await middleware._reserve(2)

    other = await asyncio.wait_for(reserve_other(), timeout=0.5)
    assert other < _PER_CHAT_INTERVAL
