"""Методы Bot API, которых ещё нет в aiogram 3.25.

Rich-сообщения появились в Bot API 10.1, а в библиотеке — только с 3.30.
Обновляться ради них не пришлось: метод целиком описывается парой моделей,
а `TelegramMethod` — обычная pydantic-модель, которую aiogram сериализует
и отправляет как любой встроенный метод.
"""

from typing import Optional, Union

from aiogram.methods import TelegramMethod
from aiogram.types import (
    InlineKeyboardMarkup,
    InputMediaAnimation,
    InputMediaAudio,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
    Message,
    TelegramObject,
)

RichMedia = Union[
    InputMediaPhoto,
    InputMediaVideo,
    InputMediaAnimation,
    InputMediaAudio,
    InputMediaDocument,
]


class InputRichMessageMedia(TelegramObject):
    """Вложение, на которое ссылается `tg://photo?id=` внутри разметки.

    `id` — произвольная метка (A-Z, a-z, 0-9, _ и -), а не file_id: file_id
    лежит внутри `media`.
    """

    id: str
    media: RichMedia


class InputRichMessage(TelegramObject):
    """Содержимое rich-сообщения. Ровно одно из `html`, `markdown`, `blocks`."""

    html: Optional[str] = None
    markdown: Optional[str] = None
    media: Optional[list[InputRichMessageMedia]] = None
    is_rtl: Optional[bool] = None
    skip_entity_detection: Optional[bool] = None


class SendRichMessage(TelegramMethod[Message]):
    """https://core.telegram.org/bots/api#sendrichmessage"""

    __returning__ = Message
    __api_method__ = "sendRichMessage"

    chat_id: Union[int, str]
    rich_message: InputRichMessage
    disable_notification: Optional[bool] = None
    protect_content: Optional[bool] = None
    reply_markup: Optional[InlineKeyboardMarkup] = None
