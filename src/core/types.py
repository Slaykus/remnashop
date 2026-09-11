from typing import TYPE_CHECKING, Annotated, Any, NewType, TypeAlias, Union

from aiogram.types import (
    ForceReply,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from pydantic import PlainValidator
from remnapy.models import UserResponseDto
from remnapy.models.webhook import UserDto as UserWebhookDto

from src.core.enums import Locale, SystemNotificationType, UserNotificationType

if TYPE_CHECKING:
    ListStr: TypeAlias = list[str]
    ListLocale: TypeAlias = list[Locale]
else:
    ListStr = NewType("ListStr", list[str])
    ListLocale = NewType("ListLocale", list[Locale])

AnyKeyboard: TypeAlias = Union[
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    ForceReply,
]


NotificationType: TypeAlias = Union[SystemNotificationType, UserNotificationType]

# Значение, которое умеет читать слой переводов: либо готовый текст, либо
# пара «ключ + параметры». Отдельный алиас вместо Any нужен, чтобы подмена
# одной формы другой была видна проверке типов, а не всплывала в чеке.
I18nValue: TypeAlias = Union[str, tuple[str, dict[str, Any]]]

RemnaUserDto: TypeAlias = Union[UserWebhookDto, UserResponseDto]

StringList: TypeAlias = Annotated[
    ListStr, PlainValidator(lambda x: [s.strip() for s in x.split(",")])
]
LocaleList: TypeAlias = Annotated[
    ListLocale,
    PlainValidator(
        func=lambda x: [Locale(loc.strip()) for loc in x.split(",")] if isinstance(x, str) else x
    ),
]
