from typing import Any

from aiogram.enums import ButtonStyle, ContentType
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from aiogram.types import BufferedInputFile

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
from src.core.constants import USER_KEY
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

    if not code or not code.isalnum():
        await notifier.notify_user(
            user,
            payload=MessagePayloadDto(i18n_key="ntf-ad.code-invalid", delete_after=5),
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
    if not message.photo:
        await notifier.notify_user(
            user, payload=MessagePayloadDto(i18n_key="ntf-common.invalid-value", delete_after=5)
        )
        return
    file_id = message.photo[-1].file_id
    link_id: int = dialog_manager.dialog_data.get("link_id")  # type: ignore[assignment]
    link = await ad_link_dao.get_by_id(link_id)
    if not link:
        return
    link.promo_photo_id = file_id
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
    text = (message.text or "").strip()
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
    label = (message.text or "").strip()
    if not label or len(label) > 100:
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

    if not url:
        url = await bot_service.get_ad_url(link.code)

    buttons = list(link.promo_buttons or [])
    if len(buttons) < 3:
        buttons.append({"label": label, "url": url, "style": style_name})
    link.promo_buttons = buttons
    await update_ad_link(user, UpdateAdLinkDto(link=link))

    dialog_manager.dialog_data.pop("new_btn_label", None)
    dialog_manager.dialog_data.pop("new_btn_url", None)
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

    deep_link = await bot_service.get_ad_url(link.code)
    style_map = {
        "primary": ButtonStyle.PRIMARY,
        "success": ButtonStyle.SUCCESS,
        "danger": ButtonStyle.DANGER,
    }

    builder = InlineKeyboardBuilder()
    for btn in (link.promo_buttons or []):
        url = btn.get("url") or deep_link
        style = style_map.get(btn.get("style", "default"))
        if style:
            builder.row(InlineKeyboardButton(text=btn["label"], url=url, style=style))
        else:
            builder.row(InlineKeyboardButton(text=btn["label"], url=url))

    if not callback.message:
        return
    markup = builder.as_markup() if link.promo_buttons else None
    if link.promo_photo_id:
        await callback.message.answer_photo(
            photo=link.promo_photo_id,
            caption=link.promo_text,
            parse_mode="HTML",
            reply_markup=markup,
        )
    else:
        await callback.message.answer(
            link.promo_text,
            parse_mode="HTML",
            reply_markup=markup,
        )
