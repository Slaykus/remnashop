from typing import Any, Awaitable, Callable, Final, Optional, cast

from aiogram.dispatcher.event.bases import UNHANDLED
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import ErrorEvent as AiogramErrorEvent
from aiogram.types import TelegramObject
from aiogram.types import User as AiogramUser
from aiogram_dialog.api.exceptions import (
    InvalidStackIdError,
    OutdatedIntent,
    UnknownIntent,
    UnknownState,
)
from dishka import AsyncContainer
from dishka.integrations.aiogram import AiogramMiddlewareData
from loguru import logger

from src.application.common import BotService, EventPublisher, Notifier
from src.application.common.dao import UserDao
from src.application.dto import MessagePayloadDto, TempUserDto
from src.application.events import ErrorEvent
from src.application.use_cases.misc.commands.navigation import RedirectMenu
from src.core.config import AppConfig
from src.core.constants import CONFIG_KEY, CONTAINER_KEY
from src.core.enums import Command, MiddlewareEventType
from src.core.exceptions import MenuRenderError, PermissionDeniedError
from src.telegram.keyboards import get_contact_support_keyboard

from .base import EventTypedMiddleware

_IGNORED_BAD_REQUESTS: Final[tuple[str, ...]] = (
    "message is not modified",
    "message to delete not found",
    "message can't be deleted",
    "query is too old and response timeout expired",
    "MESSAGE_ID_INVALID",
    "Bad Request: message to forward not found",
)


class ErrorMiddleware(EventTypedMiddleware):
    __event_types__ = [MiddlewareEventType.ERROR]

    async def middleware_logic(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        """
        Разобрать ошибку в собственной области видимости контейнера.

        Контейнер запроса к этому моменту уже закрыт: dishka оборачивает
        обработку апдейта, а обработчик ошибок стоит выше неё и получает
        управление ровно тогда, когда исключение оттуда вышло. Всё, что
        бралось из закрытого контейнера, создавалось без владельца —
        сессия базы не возвращалась в пул, и соединение висело до сборщика
        мусора, который ругался в логи на невозвращённое подключение.
        """
        stale: AsyncContainer = data[CONTAINER_KEY]
        async with (stale.parent_container or stale)(
            {TelegramObject: event, AiogramMiddlewareData: data},
        ) as container:
            return await self._handle_error(handler, event, data, container)

    async def _handle_error(  # noqa: C901
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
        container: AsyncContainer,
    ) -> Any:
        event = cast(AiogramErrorEvent, event)
        aiogram_user: Optional[AiogramUser] = self._get_aiogram_user(data)
        config: AppConfig = data[CONFIG_KEY]

        bot_service = await container.get(BotService)
        event_publisher = await container.get(EventPublisher)
        notifier = await container.get(Notifier)
        redirect_menu = await container.get(RedirectMenu)
        user_dao = await container.get(UserDao)

        is_context_loss = isinstance(
            event.exception,
            (
                InvalidStackIdError,
                OutdatedIntent,
                UnknownIntent,
                UnknownState,
            ),
        )

        if isinstance(event.exception, TelegramBadRequest):
            error_text = str(event.exception)
            if any(msg in error_text for msg in _IGNORED_BAD_REQUESTS):
                logger.warning(f"Ignored expected TelegramBadRequest: {event.exception}")
                if aiogram_user:
                    await redirect_menu.system(aiogram_user.id)
                return

        if aiogram_user:
            if isinstance(event.exception, TelegramForbiddenError):
                # TODO: handle other cases of forbidden error (e.g. blocked by user)
                return

            if isinstance(event.exception, PermissionDeniedError):
                await notifier.notify_user(
                    TempUserDto.from_aiogram(aiogram_user),
                    i18n_key="ntf-error.permission-denied",
                )
                return

            if not isinstance(event.exception, MenuRenderError):
                is_start_command = (
                    event.update.message is not None
                    and event.update.message.text == f"/{Command.START.value.command}"
                )
                if not is_start_command:
                    await redirect_menu.system(aiogram_user.id)

                if is_context_loss:
                    user = await user_dao.get_by_telegram_id(aiogram_user.id)
                    if user:
                        i18n_key = (
                            "ntf-error.lost-context"
                            if user.is_privileged
                            else "ntf-error.lost-context-restart"
                        )
                        await notifier.notify_user(user, i18n_key=i18n_key)
                else:
                    await notifier.notify_user(
                        user=TempUserDto.from_aiogram(aiogram_user),
                        payload=MessagePayloadDto(
                            i18n_key="ntf-error.unknown",
                            reply_markup=get_contact_support_keyboard(
                                bot_service.get_support_url()
                            ),
                        ),
                    )

        if is_context_loss:
            result = await handler(event, data)
            # Человек уже возвращён в меню и получил уведомление — ошибка
            # отработана. Без явного ответа aiogram считает её необработанной,
            # пробрасывает дальше и печатает полный traceback: мониторинг
            # поднимал тревогу на штатном нажатии устаревшей кнопки.
            return True if result is UNHANDLED else result

        error_event = ErrorEvent(
            **config.build.data,
            #
            telegram_id=aiogram_user.id if aiogram_user else None,
            username=aiogram_user.username if aiogram_user else None,
            name=aiogram_user.full_name if aiogram_user else None,
            #
            exception=event.exception,
        )

        await event_publisher.publish(error_event)
        logger.exception(event.exception)
