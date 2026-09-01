import hashlib
import re

from aiogram import F, Router
from aiogram.enums import ButtonStyle
from aiogram.types import (
    InlineKeyboardButton,
    InlineQuery,
    InlineQueryResultArticle,
    InlineQueryResultCachedGif,
    InlineQueryResultCachedPhoto,
    InlineQueryResultCachedVideo,
    InlineQueryResultUnion,
    InputTextMessageContent,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject
from loguru import logger

from src.application.common import BotService, TranslatorRunner
from src.application.common.dao import AdLinkDao, UserDao
from src.application.common.policy import Permission, PermissionPolicy
from src.core.constants import INLINE_QUERY_INVITE, INLINE_QUERY_PROMO_PREFIX
from src.core.enums import MediaType
from src.core.utils.converters import strip_html
from src.telegram.keyboards import get_promo_keyboard
from src.telegram.widgets import extract_tg_emoji

router = Router(name=__name__)

_TG_EMOJI_RE = re.compile(r'<tg-emoji emoji-id="\d+">([^<]*)</tg-emoji>')

# Bot API разрешает кастом-эмодзи только в личных чатах, группах и супергруппах.
# Отправка такого сообщения в канал отклоняется, поэтому туда уходит обычный
# вариант. chat_type может отсутствовать у старых клиентов — тогда тоже
# подстраховываемся обычными эмодзи: лучше проще, чем несостоявшаяся отправка.
_CUSTOM_EMOJI_CHATS = frozenset({"sender", "private", "group", "supergroup"})


def _strip_custom_emoji(text: str) -> str:
    """Разворачивает теги обратно в обычные эмодзи, оставляя запасной символ."""
    return _TG_EMOJI_RE.sub(r"\1", text)


@inject
@router.inline_query(F.query == INLINE_QUERY_INVITE)
async def handle_inline_query(
    inline_query: InlineQuery,
    user_dao: FromDishka[UserDao],
    bot_service: FromDishka[BotService],
    i18n: FromDishka[TranslatorRunner],
) -> None:
    user = await user_dao.get_by_telegram_id(inline_query.from_user.id)

    if not user:
        logger.warning(
            f"User with Telegram ID '{inline_query.from_user.id}' not found for inline query"
        )
        return

    logger.info(f"{user.log} Sent inline query {INLINE_QUERY_INVITE}")

    result_id = hashlib.md5(inline_query.query.strip().encode()).hexdigest()
    referral_url = await bot_service.get_referral_url(user.referral_code)
    bot_name = await bot_service.get_my_name()

    allow_custom_emoji = inline_query.chat_type in _CUSTOM_EMOJI_CHATS

    raw_start = i18n.get("inline-invite.start")
    if allow_custom_emoji:
        # У кнопки эмодзи живёт в отдельном поле, а не в подписи.
        start_text, start_emoji_id = extract_tg_emoji(raw_start)
    else:
        start_text, start_emoji_id = _strip_custom_emoji(raw_start), None

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=start_text,
            style=ButtonStyle.SUCCESS,
            url=referral_url,
            icon_custom_emoji_id=start_emoji_id,
        )
    )

    message_text = i18n.get("inline-invite.message", bot_name=bot_name)
    if not allow_custom_emoji:
        message_text = _strip_custom_emoji(message_text)

    results: list[InlineQueryResultUnion] = [
        InlineQueryResultArticle(
            id=result_id,
            thumbnail_url="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcT6Msm80-vY25Ecm4cOhOTAG1P21zKBax8-KA&s",
            title=i18n.get("inline-invite.title"),
            description=i18n.get("inline-invite.description"),
            input_message_content=InputTextMessageContent(message_text=message_text),
            reply_markup=builder.as_markup(),
        )
    ]

    await inline_query.answer(results, cache_time=1, is_personal=True)


@inject
@router.inline_query(F.query.startswith(INLINE_QUERY_PROMO_PREFIX))
async def handle_promo_inline_query(
    inline_query: InlineQuery,
    user_dao: FromDishka[UserDao],
    ad_link_dao: FromDishka[AdLinkDao],
    bot_service: FromDishka[BotService],
) -> None:
    """
    Отдать готовый рекламный пост прямо в канал.

    Раньше пост можно было только получить себе превью и переслать руками,
    теряя по дороге кнопки. Значение запроса готовил геттер экрана, но
    принимающей стороны у него не было.

    Право проверяем: код рекламной ссылки виден в строке запроса, и без
    проверки любой, кто его подсмотрел, публиковал бы посты от лица бота.
    """
    user = await user_dao.get_by_telegram_id(inline_query.from_user.id)
    if not user or not PermissionPolicy.has_permission(user, Permission.VIEW_ADVERTISING):
        await inline_query.answer([], cache_time=1, is_personal=True)
        return

    code = inline_query.query[len(INLINE_QUERY_PROMO_PREFIX) :].strip()
    link = await ad_link_dao.get_by_code(code)
    if link is None or not link.promo_text:
        await inline_query.answer([], cache_time=1, is_personal=True)
        return

    # Премиум-эмодзи здесь не вырезаем, в отличие от приглашения выше.
    # Рекламный пост ради них и собирают, а у бота есть право их слать.
    # Если телеграм вдруг откажется принимать такой пост в канал, лечится
    # одной строкой: прогнать promo_text через _strip_custom_emoji для тех
    # же типов чатов, что и приглашение.
    ad_url = await bot_service.get_ad_link_url(link.code)
    bot_url = await bot_service.get_ad_deeplink_url(link.code)
    markup = get_promo_keyboard(link.promo_buttons or [], ad_url, bot_url)
    result_id = hashlib.md5(f"{INLINE_QUERY_PROMO_PREFIX}{code}".encode()).hexdigest()

    result: InlineQueryResultUnion
    if link.promo_photo_id:
        # Вложение уже лежит у телеграма, поэтому берём кэшированные варианты:
        # заново выгружать файл ради каждой публикации незачем.
        cached = {
            MediaType.VIDEO: InlineQueryResultCachedVideo,
            MediaType.GIF: InlineQueryResultCachedGif,
        }.get(link.promo_media_type, InlineQueryResultCachedPhoto)
        kwargs: dict = {
            "id": result_id,
            "caption": link.promo_text,
            "parse_mode": "HTML",
            "reply_markup": markup,
        }
        if cached is InlineQueryResultCachedPhoto:
            kwargs["photo_file_id"] = link.promo_photo_id
        elif cached is InlineQueryResultCachedVideo:
            # У видео заголовок обязателен по Bot API.
            kwargs["video_file_id"] = link.promo_photo_id
            kwargs["title"] = link.name
        else:
            kwargs["gif_file_id"] = link.promo_photo_id
        result = cached(**kwargs)
    else:
        result = InlineQueryResultArticle(
            id=result_id,
            title=link.name,
            description=strip_html(link.promo_text)[:100],
            input_message_content=InputTextMessageContent(
                message_text=link.promo_text,
                parse_mode="HTML",
            ),
            reply_markup=markup,
        )

    logger.info(f"{user.log} Requested promo post for ad link '{code}'")
    await inline_query.answer([result], cache_time=1, is_personal=True)
