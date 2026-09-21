"""
Защита от лимитов телеграма на исходящих запросах.

21.09 бот на четырнадцать минут перестал отвечать всем: у одного
человека чат упёрся в лимит, а код на отказ отвечал новыми отправками,
каждая из которых упиралась в тот же лимит. Обработчик ошибок мы с тех
пор научили молчать, но это лечит следствие. Здесь — причина: бот не
умел притормаживать.

Два слоя, и нужны оба.

Упреждающий держит темп в рамках, о которых телеграм пишет открыто:
примерно тридцать запросов в секунду на бота и примерно одно сообщение
в секунду в один чат. Берём с запасом.

Ответный выполняет просьбу 'retry after N', когда лимит всё же настал:
ждёт названное время и повторяет. Это безопасно — ответ 429 означает,
что сообщение не доставлено, и повтор не создаст второго.

Слой резервирования устроен как расписание: запрос занимает ближайшее
свободное место и ждёт до него. Ожидание всегда снаружи блокировки,
иначе очередь в один чат останавливала бы всех остальных.
"""

import asyncio
import time
from typing import Any, Final, Optional

from aiogram import Bot
from aiogram.client.session.middlewares.base import (
    BaseRequestMiddleware,
    NextRequestMiddlewareType,
)
from aiogram.exceptions import TelegramRetryAfter
from aiogram.methods import Response, TelegramMethod
from aiogram.methods.base import TelegramType
from loguru import logger

# Телеграм: ~30 запросов в секунду на бота. Берём 25 — запас на то, что
# наш счётчик и счётчик телеграма меряют время чуть по-разному.
_GLOBAL_PER_SECOND: Final[float] = 25.0

# Телеграм: ~1 сообщение в секунду в один чат. Секунда ровно слишком
# близко к краю, добавляем немного.
_PER_CHAT_INTERVAL: Final[float] = 1.05

# Сколько ждать своей очереди максимум. Дальше отправляем как есть: лучше
# получить отказ и отработать его ниже, чем держать задачу бесконечно.
_MAX_WAIT: Final[float] = 30.0

# Повторов после отказа. Больше трёх не нужно: если телеграм просит ждать
# в четвёртый раз, проблема не в темпе.
_MAX_RETRIES: Final[int] = 3

# Дольше этого ждать по просьбе телеграма не станем — такие паузы бывают
# при блокировках, и держать ради них задачу смысла нет.
_MAX_RETRY_AFTER: Final[float] = 60.0

_CHATS_SOFT_LIMIT: Final[int] = 10_000

# Лимит «одно сообщение в секунду» — про отправку сообщений. Правку и
# удаление он не трогает, и накладывать его на них нельзя: перерисовка
# экрана в диалоге это удаление плюс отправка, и человек ждал бы две
# секунды вместо одной на каждое нажатие.
_SENDING_PREFIX: Final[str] = "Send"


class FloodControlMiddleware(BaseRequestMiddleware):
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._global_next = 0.0
        self._chat_next: dict[Any, float] = {}

    async def __call__(
        self,
        make_request: NextRequestMiddlewareType[TelegramType],
        bot: Bot,
        method: TelegramMethod[TelegramType],
    ) -> Response[TelegramType]:
        chat_id = self._chat_key(method)

        for attempt in range(_MAX_RETRIES + 1):
            await self._wait_for_slot(chat_id)
            try:
                return await make_request(bot, method)
            except TelegramRetryAfter as error:
                delay = float(getattr(error, "retry_after", 1) or 1)

                if attempt >= _MAX_RETRIES or delay > _MAX_RETRY_AFTER:
                    logger.warning(
                        f"Giving up on '{type(method).__name__}' after "
                        f"{attempt + 1} attempt(s), Telegram asks for {delay}s"
                    )
                    raise

                # Двигаем расписание для всех, а не только для себя: отказ
                # означает, что наш темп телеграму уже не понравился.
                self._push_back(chat_id, delay)
                logger.warning(
                    f"Telegram asks to wait {delay}s on '{type(method).__name__}', "
                    f"retry {attempt + 1} of {_MAX_RETRIES}"
                )
                await asyncio.sleep(delay + 0.5)

        # Недостижимо: цикл либо вернёт ответ, либо поднимет исключение.
        raise RuntimeError("Flood control middleware exhausted its retries")

    @staticmethod
    def _chat_key(method: TelegramMethod[TelegramType]) -> Optional[Any]:
        if not type(method).__name__.startswith(_SENDING_PREFIX):
            return None
        return getattr(method, "chat_id", None)

    async def _wait_for_slot(self, chat_id: Optional[Any]) -> None:
        try:
            delay = await self._reserve(chat_id)
        except Exception as error:
            # Расписание — удобство, а не обязанность. Если оно сломалось,
            # отправляем без него: отказ телеграма мы переживём, а молчащий
            # бот — нет.
            logger.warning(f"Flood control scheduling skipped: {error}")
            return

        if delay > 0:
            await asyncio.sleep(delay)

    async def _reserve(self, chat_id: Optional[Any]) -> float:
        now = time.monotonic()
        global_step = 1.0 / _GLOBAL_PER_SECOND

        async with self._lock:
            start = max(now, self._global_next)
            if chat_id is not None:
                start = max(start, self._chat_next.get(chat_id, 0.0))

            self._global_next = start + global_step
            if chat_id is not None:
                self._chat_next[chat_id] = start + _PER_CHAT_INTERVAL
                self._forget_stale(now)

        return min(max(0.0, start - now), _MAX_WAIT)

    def _push_back(self, chat_id: Optional[Any], delay: float) -> None:
        deadline = time.monotonic() + delay
        self._global_next = max(self._global_next, deadline)
        if chat_id is not None:
            self._chat_next[chat_id] = max(self._chat_next.get(chat_id, 0.0), deadline)

    def _forget_stale(self, now: float) -> None:
        """Чаты, чья очередь давно прошла, помнить незачем."""
        if len(self._chat_next) <= _CHATS_SOFT_LIMIT:
            return
        self._chat_next = {
            chat: until for chat, until in self._chat_next.items() if until > now
        }
