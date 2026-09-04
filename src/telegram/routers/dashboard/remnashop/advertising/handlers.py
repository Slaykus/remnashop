from typing import Any, Optional

from aiogram import Bot
from aiogram.enums import ButtonStyle, ContentType
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message, MessageEntity
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject
from loguru import logger

from aiogram.types import (
    BufferedInputFile,
    InputMediaAnimation,
    InputMediaDocument,
    InputMediaPhoto,
    InputMediaVideo,
)

from src.application.common import Notifier
from src.application.common.dao.ad_link import AdLinkDao
from src.application.dto import UserDto
from src.application.dto.message_payload import MessagePayloadDto
from src.application.common import BotService
from src.application.use_cases.ad_link.commands.crud import (
    CreateAdLink,
    CreateAdLinkDto,
    DeleteAdLink,
    DeleteAdLinkDto,
    UpdateAdLink,
    UpdateAdLinkDto,
)
from src.application.use_cases.ad_link.queries.list import (
    GetAdLinkDailyStats,
    GetAdLinkDailyStatsInput,
    GetAdLinkPeriodStats,
    GetAdLinkPeriodStatsInput,
    GetAllAdLinksComparison,
)
from src.application.dto import AdLinkDto
from src.core.enums import MediaType, TextFormat
from src.telegram.keyboards import get_promo_keyboard
from src.telegram.methods import (
    InputRichMessage,
    InputRichMessageMedia,
    SendRichMessage,
)
from src.core.constants import AD_LINK_CODE_PATTERN, USER_KEY
from src.telegram.charts import (
    build_comparison_chart,
    build_daily_clicks_chart,
    build_funnel_chart,
    render_chart,
)
from src.telegram.states import RemnashopAdvertising
from src.telegram.utils import is_double_click


@inject
async def on_link_select(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
    item_id: int,
    ad_link_dao: FromDishka[AdLinkDao],
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    dialog_manager.dialog_data["link_id"] = item_id

    link = await ad_link_dao.get_by_id(item_id)
    if link:
        dialog_manager.dialog_data["delete_name"] = link.name

    await dialog_manager.switch_to(RemnashopAdvertising.VIEW)


@inject
async def on_toggle_active(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    ad_link_dao: FromDishka[AdLinkDao],
    update_ad_link: FromDishka[UpdateAdLink],
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    link_id: int = dialog_manager.dialog_data.get("link_id")  # type: ignore[assignment]
    link = await ad_link_dao.get_by_id(link_id)
    if not link:
        return
    link.is_active = not link.is_active
    await update_ad_link(user, UpdateAdLinkDto(link=link))


@inject
async def on_create_name_input(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    notifier: FromDishka[Notifier],
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    name = (message.text or "").strip()
    if not name:
        user: UserDto = dialog_manager.middleware_data[USER_KEY]
        await notifier.notify_user(
            user,
            payload=MessagePayloadDto(i18n_key="ntf-common.invalid-value", delete_after=5),
        )
        return
    dialog_manager.dialog_data["create_name"] = name
    await dialog_manager.switch_to(RemnashopAdvertising.CREATE_CODE)


@inject
async def on_create_code_input(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    ad_link_dao: FromDishka[AdLinkDao],
    create_ad_link: FromDishka[CreateAdLink],
    notifier: FromDishka[Notifier],
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    code = (message.text or "").strip()

    # Ключ 'ntf-ad.code-invalid' говорит «ссылка не найдена» — текст достался
    # ему от другого сценария и здесь только путал. Берём общий про
    # некорректное значение, тот же, что ниже показывается на занятый код.
    if not AD_LINK_CODE_PATTERN.match(code):
        await notifier.notify_user(
            user,
            payload=MessagePayloadDto(i18n_key="ntf-common.invalid-value", delete_after=5),
        )
        return

    existing = await ad_link_dao.get_by_code(code)
    if existing:
        await notifier.notify_user(
            user,
            payload=MessagePayloadDto(i18n_key="ntf-common.invalid-value", delete_after=5),
        )
        return

    name: str = dialog_manager.dialog_data.get("create_name", "")
    link = await create_ad_link(
        user,
        CreateAdLinkDto(name=name, code=code),
    )
    dialog_manager.dialog_data["link_id"] = link.id
    dialog_manager.dialog_data["delete_name"] = link.name
    await dialog_manager.switch_to(RemnashopAdvertising.VIEW)


@inject
async def on_edit_name_input(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    ad_link_dao: FromDishka[AdLinkDao],
    update_ad_link: FromDishka[UpdateAdLink],
    notifier: FromDishka[Notifier],
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    name = (message.text or "").strip()
    if not name:
        await notifier.notify_user(
            user,
            payload=MessagePayloadDto(i18n_key="ntf-common.invalid-value", delete_after=5),
        )
        return
    link_id: int = dialog_manager.dialog_data.get("link_id")  # type: ignore[assignment]
    link = await ad_link_dao.get_by_id(link_id)
    if not link:
        return
    link.name = name
    await update_ad_link(user, UpdateAdLinkDto(link=link))
    dialog_manager.dialog_data["delete_name"] = name
    await dialog_manager.switch_to(RemnashopAdvertising.VIEW)


@inject
async def on_edit_bonus_points_input(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    ad_link_dao: FromDishka[AdLinkDao],
    update_ad_link: FromDishka[UpdateAdLink],
    notifier: FromDishka[Notifier],
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    try:
        value = int((message.text or "").strip())
        if value < 0:
            raise ValueError
    except ValueError:
        await notifier.notify_user(
            user,
            payload=MessagePayloadDto(i18n_key="ntf-common.invalid-value", delete_after=5),
        )
        return
    link_id: int = dialog_manager.dialog_data.get("link_id")  # type: ignore[assignment]
    link = await ad_link_dao.get_by_id(link_id)
    if not link:
        return
    link.bonus_points = value
    await update_ad_link(user, UpdateAdLinkDto(link=link))
    await dialog_manager.switch_to(RemnashopAdvertising.VIEW)


@inject
async def on_edit_bonus_days_input(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    ad_link_dao: FromDishka[AdLinkDao],
    update_ad_link: FromDishka[UpdateAdLink],
    notifier: FromDishka[Notifier],
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    try:
        value = int((message.text or "").strip())
        if value < 0:
            raise ValueError
    except ValueError:
        await notifier.notify_user(
            user,
            payload=MessagePayloadDto(i18n_key="ntf-common.invalid-value", delete_after=5),
        )
        return
    link_id: int = dialog_manager.dialog_data.get("link_id")  # type: ignore[assignment]
    link = await ad_link_dao.get_by_id(link_id)
    if not link:
        return
    link.bonus_days = value
    await update_ad_link(user, UpdateAdLinkDto(link=link))
    await dialog_manager.switch_to(RemnashopAdvertising.VIEW)


@inject
async def on_edit_bonus_discount_input(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    ad_link_dao: FromDishka[AdLinkDao],
    update_ad_link: FromDishka[UpdateAdLink],
    notifier: FromDishka[Notifier],
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    try:
        value = int((message.text or "").strip())
        if value < 0 or value > 100:
            raise ValueError
    except ValueError:
        await notifier.notify_user(
            user,
            payload=MessagePayloadDto(i18n_key="ntf-common.invalid-value", delete_after=5),
        )
        return
    link_id: int = dialog_manager.dialog_data.get("link_id")  # type: ignore[assignment]
    link = await ad_link_dao.get_by_id(link_id)
    if not link:
        return
    link.bonus_discount_pct = value
    await update_ad_link(user, UpdateAdLinkDto(link=link))
    await dialog_manager.switch_to(RemnashopAdvertising.VIEW)


@inject
async def on_delete_confirm(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    delete_ad_link: FromDishka[DeleteAdLink],
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    if not is_double_click(dialog_manager, "delete_confirm"):
        return
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    link_id: int = dialog_manager.dialog_data.get("link_id")  # type: ignore[assignment]
    await delete_ad_link(user, DeleteAdLinkDto(link_id=link_id))
    await dialog_manager.switch_to(RemnashopAdvertising.LIST)


# ── Promo message handlers ─────────────────────────────────────────────────────


@inject
async def on_promo_set_photo(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    ad_link_dao: FromDishka[AdLinkDao],
    update_ad_link: FromDishka[UpdateAdLink],
    notifier: FromDishka[Notifier],
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    # Тип определяем так же, как в рассылке. Документы и стикеры сюда не
    # берём: рекламный пост — это картинка, ролик или гифка.
    media_type: Optional[MediaType] = None
    file_id: Optional[str] = None
    if message.photo:
        media_type = MediaType.PHOTO
        file_id = message.photo[-1].file_id
    elif message.video:
        media_type = MediaType.VIDEO
        file_id = message.video.file_id
    elif message.animation:
        media_type = MediaType.GIF
        file_id = message.animation.file_id

    if not file_id:
        await notifier.notify_user(
            user, payload=MessagePayloadDto(i18n_key="ntf-common.invalid-value", delete_after=5)
        )
        return
    link_id: int = dialog_manager.dialog_data.get("link_id")  # type: ignore[assignment]
    link = await ad_link_dao.get_by_id(link_id)
    if not link:
        return
    link.promo_photo_id = file_id
    link.promo_media_type = media_type
    await update_ad_link(user, UpdateAdLinkDto(link=link))
    await dialog_manager.switch_to(RemnashopAdvertising.PROMO)


@inject
async def on_promo_remove_photo(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    ad_link_dao: FromDishka[AdLinkDao],
    update_ad_link: FromDishka[UpdateAdLink],
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    link_id: int = dialog_manager.dialog_data.get("link_id")  # type: ignore[assignment]
    link = await ad_link_dao.get_by_id(link_id)
    if not link:
        return
    link.promo_photo_id = None
    link.promo_media_type = None
    await update_ad_link(user, UpdateAdLinkDto(link=link))
    await dialog_manager.switch_to(RemnashopAdvertising.PROMO)


@inject
async def on_promo_set_text(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    ad_link_dao: FromDishka[AdLinkDao],
    update_ad_link: FromDishka[UpdateAdLink],
    notifier: FromDishka[Notifier],
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    # html_text, а не text: жирный, ссылки и премиум-эмодзи живут в entities,
    # и при сохранении голого текста терялись без следа. Пост уходит с
    # parse_mode=HTML, так что разметка доезжает до читателя как есть.
    text = (message.html_text or "").strip() if message.text else ""
    if not text:
        await notifier.notify_user(
            user, payload=MessagePayloadDto(i18n_key="ntf-common.invalid-value", delete_after=5)
        )
        return
    link_id: int = dialog_manager.dialog_data.get("link_id")  # type: ignore[assignment]
    link = await ad_link_dao.get_by_id(link_id)
    if not link:
        return
    link.promo_text = text
    link.promo_format = TextFormat.HTML
    await update_ad_link(user, UpdateAdLinkDto(link=link))
    await dialog_manager.switch_to(RemnashopAdvertising.PROMO)


def _inline_custom_emoji(text: str, entities: Optional[list[MessageEntity]]) -> str:
    """Вернуть премиум-эмодзи в текст разметкой `![…](tg://emoji?id=…)`.

    В сообщении они лежат отдельно от текста: на месте эмодзи стоит обычный
    запасной символ, а идентификатор — в entities. Сохраняя голый text, мы
    теряли идентификатор, и в посте оставалась обычная картинка.

    Смещения телеграм считает в кодовых единицах UTF-16, а не в символах
    питона, поэтому режем по закодированной строке.
    """
    found = [e for e in (entities or []) if e.type == "custom_emoji"]
    if not found:
        return text

    data = text.encode("utf-16-le")
    parts: list[str] = []
    pos = 0
    for entity in sorted(found, key=lambda e: e.offset):
        start = entity.offset * 2
        end = start + entity.length * 2
        parts.append(data[pos:start].decode("utf-16-le"))
        fallback = data[start:end].decode("utf-16-le")
        parts.append(f"![{fallback}](tg://emoji?id={entity.custom_emoji_id})")
        pos = end
    parts.append(data[pos:].decode("utf-16-le"))
    return "".join(parts)


@inject
async def on_promo_set_markdown(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    ad_link_dao: FromDishka[AdLinkDao],
    update_ad_link: FromDishka[UpdateAdLink],
    notifier: FromDishka[Notifier],
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    # Здесь наоборот нужен голый text: человек присылает разметку как есть,
    # и html_text экранировал бы её собственные символы. Премиум-эмодзи при
    # этом остались бы обычными — они живут не в тексте, а в entities, —
    # поэтому вписываем их обратно синтаксисом разметки.
    text = _inline_custom_emoji(message.text or "", message.entities).strip()
    if not text:
        await notifier.notify_user(
            user, payload=MessagePayloadDto(i18n_key="ntf-common.invalid-value", delete_after=5)
        )
        return
    link_id: int = dialog_manager.dialog_data.get("link_id")  # type: ignore[assignment]
    link = await ad_link_dao.get_by_id(link_id)
    if not link:
        return
    link.promo_text = text
    link.promo_format = TextFormat.MARKDOWN
    await update_ad_link(user, UpdateAdLinkDto(link=link))
    await dialog_manager.switch_to(RemnashopAdvertising.PROMO)


@inject
async def on_promo_button_label_input(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    notifier: FromDishka[Notifier],
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    # html_text: премиум-эмодзи в подписи живёт в entities, и при сохранении
    # голого текста от него оставался только запасной символ. На самой кнопке
    # телеграм эмодзи в тексте не рисует — сборщик клавиатуры переносит его
    # в отдельное поле иконки.
    label = (message.html_text or "").strip() if message.text else ""
    if not label or len(message.text or "") > 100:
        await notifier.notify_user(
            user, payload=MessagePayloadDto(i18n_key="ntf-common.invalid-value", delete_after=5)
        )
        return
    dialog_manager.dialog_data["new_btn_label"] = label
    await dialog_manager.switch_to(RemnashopAdvertising.PROMO_BUTTON_URL)


@inject
async def on_promo_button_url_input(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    notifier: FromDishka[Notifier],
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    url = (message.text or "").strip()
    if not url.startswith("https://"):
        await notifier.notify_user(
            user, payload=MessagePayloadDto(i18n_key="ntf-common.invalid-value", delete_after=5)
        )
        return
    dialog_manager.dialog_data["new_btn_url"] = url
    await dialog_manager.switch_to(RemnashopAdvertising.PROMO_BUTTON_STYLE)


@inject
async def on_promo_use_ad_url(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    dialog_manager.dialog_data["new_btn_url"] = ""
    # Куда вести, решаем по нажатой кнопке, а адрес подставляется при показе
    # поста: вмороженный адрес не переживал смену настроек.
    dialog_manager.dialog_data["new_btn_target"] = (
        "bot" if widget.widget_id == "promo_use_bot_url" else "site"
    )
    await dialog_manager.switch_to(RemnashopAdvertising.PROMO_BUTTON_STYLE)


_STYLE_MAP = {
    "style_default": None,
    "style_primary": ButtonStyle.PRIMARY,
    "style_success": ButtonStyle.SUCCESS,
    "style_danger": ButtonStyle.DANGER,
}


@inject
async def on_promo_set_style(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    ad_link_dao: FromDishka[AdLinkDao],
    update_ad_link: FromDishka[UpdateAdLink],
    bot_service: FromDishka[BotService],
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    style_key = widget.widget_id  # "style_default" / "style_primary" / etc.
    style_name = style_key.removeprefix("style_")

    label: str = dialog_manager.dialog_data.get("new_btn_label", "")
    url: str = dialog_manager.dialog_data.get("new_btn_url", "")

    link_id: int = dialog_manager.dialog_data.get("link_id")  # type: ignore[assignment]
    link = await ad_link_dao.get_by_id(link_id)
    if not link:
        return

    target: str = dialog_manager.dialog_data.get("new_btn_target", "")
    if not url and not target:
        url = await bot_service.get_ad_link_url(link.code)

    buttons = list(link.promo_buttons or [])
    if len(buttons) < 3:
        button = {"label": label, "url": url, "style": style_name}
        if target:
            button["target"] = target
        buttons.append(button)
    link.promo_buttons = buttons
    await update_ad_link(user, UpdateAdLinkDto(link=link))

    dialog_manager.dialog_data.pop("new_btn_label", None)
    dialog_manager.dialog_data.pop("new_btn_url", None)
    dialog_manager.dialog_data.pop("new_btn_target", None)
    await dialog_manager.switch_to(RemnashopAdvertising.PROMO)


@inject
async def on_delete_promo_button(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    ad_link_dao: FromDishka[AdLinkDao],
    update_ad_link: FromDishka[UpdateAdLink],
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    # widget ids: "del_btn_0", "del_btn_1", "del_btn_2"
    index = int(widget.widget_id.split("_")[-1])
    link_id: int = dialog_manager.dialog_data.get("link_id")  # type: ignore[assignment]
    link = await ad_link_dao.get_by_id(link_id)
    if not link:
        return
    buttons = list(link.promo_buttons or [])
    if index < len(buttons):
        buttons.pop(index)
    link.promo_buttons = buttons
    await update_ad_link(user, UpdateAdLinkDto(link=link))


# ── Analytics handlers ────────────────────────────────────────────────────────


async def on_set_analytics_period(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    period_map = {"period_7": 7, "period_30": 30, "period_0": 0}
    days = period_map.get(widget.widget_id, 30)
    dialog_manager.dialog_data["analytics_period_days"] = days


@inject
async def on_send_trend_chart(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    get_ad_link_daily_stats: FromDishka[GetAdLinkDailyStats],
    ad_link_dao: FromDishka[AdLinkDao],
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    link_id: int = dialog_manager.dialog_data.get("link_id")  # type: ignore[assignment]
    days: int = dialog_manager.dialog_data.get("analytics_period_days", 30)

    link = await ad_link_dao.get_by_id(link_id)
    if not link or not callback.message:
        return

    days_data = await get_ad_link_daily_stats(
        user, GetAdLinkDailyStatsInput(link_id=link_id, days=days)
    )
    if not days_data:
        await callback.answer("Нет данных за выбранный период", show_alert=False)
        return

    config = build_daily_clicks_chart(link.name, days_data)
    png = await render_chart(config)
    await callback.message.answer_photo(
        photo=BufferedInputFile(png, filename="trend.png"),
        caption=f"📈 Тренд кликов — {link.name}",
    )


@inject
async def on_send_funnel_chart(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    get_ad_link_period_stats: FromDishka[GetAdLinkPeriodStats],
    ad_link_dao: FromDishka[AdLinkDao],
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    link_id: int = dialog_manager.dialog_data.get("link_id")  # type: ignore[assignment]
    days: int = dialog_manager.dialog_data.get("analytics_period_days", 30)

    link = await ad_link_dao.get_by_id(link_id)
    if not link or not callback.message:
        return

    stats = await get_ad_link_period_stats(
        user, GetAdLinkPeriodStatsInput(link_id=link_id, days=days)
    )
    config = build_funnel_chart(link.name, stats)
    png = await render_chart(config)
    await callback.message.answer_photo(
        photo=BufferedInputFile(png, filename="funnel.png"),
        caption=f"📊 Воронка конверсии — {link.name}",
    )


# ── Comparison handlers ────────────────────────────────────────────────────────


async def on_set_comparison_sort(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    sort_map = {"sort_revenue": "revenue", "sort_conversion": "conversion", "sort_clicks": "clicks"}
    dialog_manager.dialog_data["comparison_sort"] = sort_map.get(widget.widget_id, "revenue")


@inject
async def on_send_comparison_chart(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    get_all_comparison: FromDishka[GetAllAdLinksComparison],
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    sort: str = dialog_manager.dialog_data.get("comparison_sort", "revenue")

    if not callback.message:
        return

    items = await get_all_comparison(user)
    if not items:
        await callback.answer("Нет данных", show_alert=False)
        return

    config = build_comparison_chart(items, sort)
    png = await render_chart(config, width=800, height=max(300, len(items) * 40))
    metric_label = {"revenue": "Выручка", "conversion": "Конверсия", "clicks": "Клики"}.get(sort, sort)
    await callback.message.answer_photo(
        photo=BufferedInputFile(png, filename="comparison.png"),
        caption=f"📊 Сравнение кампаний — {metric_label}",
    )


@inject
async def on_promo_send_target(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    ad_link_dao: FromDishka[AdLinkDao],
    bot_service: FromDishka[BotService],
    notifier: FromDishka[Notifier],
) -> None:
    """
    Публикация от имени бота в указанный чат.

    Адресат берётся из пересланного сообщения либо из @имени или id —
    первый способ надёжнее, потому что не требует помнить формат.
    """
    dialog_manager.show_mode = ShowMode.EDIT
    user: UserDto = dialog_manager.middleware_data[USER_KEY]

    target: int | str | None = None
    if message.forward_from_chat is not None:
        target = message.forward_from_chat.id
    elif message.text:
        raw = message.text.strip()
        if raw.startswith("@") and len(raw) > 1:
            target = raw
        elif raw.lstrip("-").isdigit():
            target = int(raw)

    if target is None:
        await notifier.notify_user(
            user, payload=MessagePayloadDto(i18n_key="ntf-common.invalid-value", delete_after=5)
        )
        return

    # Адресата разбираем сразу: опечатка в имени должна всплыть здесь, а не
    # после подтверждения, когда человек уже решил, что пост ушёл.
    try:
        chat = await message.bot.get_chat(target)
    except Exception as e:
        logger.warning(f"{user.log} Unknown promo target '{target}': {e}")
        await notifier.notify_user(
            user,
            payload=MessagePayloadDto(
                i18n_key="ntf-ad.publish-failed",
                i18n_kwargs={"reason": str(e)[:200]},
                delete_after=15,
            ),
        )
        return

    dialog_manager.dialog_data["send_chat_id"] = chat.id
    dialog_manager.dialog_data["send_chat_title"] = chat.title or chat.full_name or str(chat.id)
    dialog_manager.dialog_data["send_is_channel"] = chat.type == "channel"
    await dialog_manager.switch_to(RemnashopAdvertising.PROMO_SEND_CONFIRM)


@inject
async def on_promo_send_confirm(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    ad_link_dao: FromDishka[AdLinkDao],
    bot_service: FromDishka[BotService],
    notifier: FromDishka[Notifier],
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    user: UserDto = dialog_manager.middleware_data[USER_KEY]
    chat_id = dialog_manager.dialog_data.get("send_chat_id")
    link_id: int = dialog_manager.dialog_data.get("link_id")  # type: ignore[assignment]
    link = await ad_link_dao.get_by_id(link_id)
    if not link or not link.promo_text or chat_id is None:
        return

    try:
        await send_promo_post(
            callback.message.bot,  # type: ignore[union-attr]
            chat_id,
            link,
            bot_service,
            staging_chat_id=user.telegram_id,
        )
    except Exception as e:
        # Показываем причину как есть: почти всегда это «бот не админ» или
        # закрытая публикация, и человеку важнее текст телеграма, чем общая фраза.
        logger.warning(f"{user.log} Failed to publish promo to '{chat_id}': {e}")
        await notifier.notify_user(
            user,
            payload=MessagePayloadDto(
                i18n_key="ntf-ad.publish-failed",
                i18n_kwargs={"reason": str(e)[:200]},
                delete_after=15,
            ),
        )
        return

    logger.info(f"{user.log} Published promo for '{link.code}' to '{chat_id}'")
    await notifier.notify_user(
        user, payload=MessagePayloadDto(i18n_key="ntf-ad.publish-ok", delete_after=5)
    )
    await dialog_manager.switch_to(RemnashopAdvertising.PROMO)


async def on_promo_send(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    await dialog_manager.switch_to(RemnashopAdvertising.PROMO_SEND_TARGET)


async def send_promo_post(
    bot: Bot,
    chat_id: int | str,
    link: AdLinkDto,
    bot_service: BotService,
    staging_chat_id: int | None = None,
) -> Message:
    """
    Отправить рекламный пост от имени бота.

    Премиум-эмодзи телеграм срезает у сообщений бота в каналах — проверено
    ответом API: сущность не доезжает. Зато при пересылке она переносится
    как есть, потому что сообщение не создаётся заново. Поэтому в канал
    отправляем в два шага: сначала в личку, где эмодзи принимаются, оттуда
    пересылаем. URL-кнопки пересылку тоже переживают.

    Без staging_chat_id шлём напрямую: в личке и группах эмодзи и так
    доезжают, лишний шаг там ни к чему.
    """
    if staging_chat_id is not None and str(staging_chat_id) != str(chat_id):
        staged = await send_promo_post(bot, staging_chat_id, link, bot_service)
        sent = await bot.forward_message(
            chat_id=chat_id,
            from_chat_id=staging_chat_id,
            message_id=staged.message_id,
        )
        # Промежуточную копию убираем: она нужна была только как источник
        # пересылки. Уже отправленный пост от её удаления не страдает.
        try:
            await bot.delete_message(chat_id=staging_chat_id, message_id=staged.message_id)
        except Exception as e:
            logger.debug(f"[AdLink] Staging copy left in chat '{staging_chat_id}': {e}")
        return sent

    ad_url = await bot_service.get_ad_link_url(link.code)
    bot_url = await bot_service.get_ad_deeplink_url(link.code)
    markup = get_promo_keyboard(link.promo_buttons or [], ad_url, bot_url)

    if link.promo_format == TextFormat.MARKDOWN:
        return await _send_rich_promo(bot, chat_id, link, markup)

    if link.promo_photo_id:
        # Тип пуст у ссылок, заведённых до поддержки видео — это фото.
        send = {
            MediaType.VIDEO: bot.send_video,
            MediaType.GIF: bot.send_animation,
        }.get(link.promo_media_type, bot.send_photo)
        return await send(
            chat_id=chat_id,
            **{_MEDIA_ARG[link.promo_media_type or MediaType.PHOTO]: link.promo_photo_id},
            caption=link.promo_text,
            parse_mode="HTML",
            reply_markup=markup,
        )

    return await bot.send_message(
        chat_id=chat_id,
        text=link.promo_text or "",
        parse_mode="HTML",
        reply_markup=markup,
    )


_MEDIA_ARG = {
    MediaType.PHOTO: "photo",
    MediaType.VIDEO: "video",
    MediaType.GIF: "animation",
}

# Схема ссылки и класс вложения для rich-сообщения. Гифка ходит по video:
# document телеграм на анимации отклоняет (RICH_MESSAGE_DOCUMENT_INVALID).
_RICH_MEDIA = {
    MediaType.PHOTO: ("photo", InputMediaPhoto),
    MediaType.VIDEO: ("video", InputMediaVideo),
    MediaType.GIF: ("video", InputMediaAnimation),
    MediaType.DOCUMENT: ("document", InputMediaDocument),
}

_RICH_MEDIA_ID = "m1"


async def _send_rich_promo(
    bot: Bot,
    chat_id: int | str,
    link: AdLinkDto,
    markup: Optional[Any],
) -> Message:
    """Пост, написанный разметкой: заголовки, списки, таблицы, цитаты.

    Вложение здесь отдельный блок, а не подпись под картинкой, — в
    rich-сообщении медиа иначе не живёт. Файл переиспользуем по file_id,
    заново он не загружается.
    """
    body = link.promo_text or ""

    media: list[InputRichMessageMedia] = []
    if link.promo_photo_id:
        scheme, factory = _RICH_MEDIA[link.promo_media_type or MediaType.PHOTO]
        media.append(
            InputRichMessageMedia(
                id=_RICH_MEDIA_ID,
                media=factory(media=link.promo_photo_id),
            )
        )
        body = f"![](tg://{scheme}?id={_RICH_MEDIA_ID})\n\n{body}"

    return await bot(
        SendRichMessage(
            chat_id=chat_id,
            rich_message=InputRichMessage(markdown=body, media=media or None),
            reply_markup=markup,
        )
    )


@inject
async def on_send_promo_preview(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    ad_link_dao: FromDishka[AdLinkDao],
    bot_service: FromDishka[BotService],
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    link_id: int = dialog_manager.dialog_data.get("link_id")  # type: ignore[assignment]
    link = await ad_link_dao.get_by_id(link_id)
    if not link or not link.promo_text:
        return

    if not callback.message:
        return

    await send_promo_post(callback.message.bot, callback.message.chat.id, link, bot_service)
