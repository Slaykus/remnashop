from typing import Any

from aiogram_dialog import DialogManager
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from src.application.common.dao.ad_link import AdLinkDao
from src.application.services import BotService
from src.application.use_cases.ad_link.queries.list import GetAdLinkStats, GetAdLinks
from src.core.constants import INLINE_QUERY_PROMO_PREFIX, USER_KEY


@inject
async def list_getter(
    dialog_manager: DialogManager,
    get_ad_links: FromDishka[GetAdLinks],
    **kwargs: Any,
) -> dict[str, Any]:
    user = dialog_manager.middleware_data[USER_KEY]
    links = await get_ad_links(user)
    return {
        "links": [
            {
                "id": link.id,
                "name": link.name,
                "code": link.code,
                "clicks_count": link.clicks_count,
                "is_active": int(link.is_active),
            }
            for link in links
        ],
        "count": len(links),
    }


@inject
async def view_getter(
    dialog_manager: DialogManager,
    ad_link_dao: FromDishka[AdLinkDao],
    get_ad_link_stats: FromDishka[GetAdLinkStats],
    bot_service: FromDishka[BotService],
    **kwargs: Any,
) -> dict[str, Any]:
    user = dialog_manager.middleware_data[USER_KEY]
    link_id: int = dialog_manager.dialog_data.get("link_id")  # type: ignore[assignment]
    link = await ad_link_dao.get_by_id(link_id)
    if not link:
        return {}

    stats = await get_ad_link_stats(user, link.id)
    deep_link = await bot_service.get_ad_url(link.code)

    return {
        "link_id": link.id,
        "name": link.name,
        "code": link.code,
        "is_active": int(link.is_active),
        "bonus_points": link.bonus_points,
        "bonus_days": link.bonus_days,
        "bonus_discount_pct": link.bonus_discount_pct,
        "clicks_count": link.clicks_count,
        "deep_link": deep_link,
        "unique_clicks": stats.unique_clicks,
        "bonus_issued_count": stats.bonus_issued_count,
        "trial_count": stats.trial_count,
        "paid_count": stats.paid_count,
        "revenue_rub": int(stats.revenue_rub),
    }


async def create_name_getter(
    dialog_manager: DialogManager, **kwargs: Any
) -> dict[str, Any]:
    return {}


async def create_code_getter(
    dialog_manager: DialogManager, **kwargs: Any
) -> dict[str, Any]:
    return {"create_name": dialog_manager.dialog_data.get("create_name", "")}


async def edit_getter(
    dialog_manager: DialogManager, **kwargs: Any
) -> dict[str, Any]:
    return {}


async def confirm_delete_getter(
    dialog_manager: DialogManager, **kwargs: Any
) -> dict[str, Any]:
    return {"delete_name": dialog_manager.dialog_data.get("delete_name", "")}


_STYLE_EMOJI = {"default": "⚪", "primary": "🔵", "success": "🟢", "danger": "🔴"}


@inject
async def promo_getter(
    dialog_manager: DialogManager,
    ad_link_dao: FromDishka[AdLinkDao],
    bot_service: FromDishka[BotService],
    **kwargs: Any,
) -> dict[str, Any]:
    link_id: int = dialog_manager.dialog_data.get("link_id")  # type: ignore[assignment]
    link = await ad_link_dao.get_by_id(link_id)
    if not link:
        return {}

    deep_link = await bot_service.get_ad_url(link.code)
    buttons = link.promo_buttons or []

    lines = []
    for i, btn in enumerate(buttons, 1):
        emoji = _STYLE_EMOJI.get(btn.get("style", "default"), "⚪")
        url = btn.get("url") or deep_link
        url_short = "→ ссылка бота" if url == deep_link else f"→ {url[:30]}"
        lines.append(f"{i}. {emoji} {btn['label']} {url_short}")

    btn_count = len(buttons)
    return {
        "name": link.name,
        "code": link.code,
        "inline_query": f"{INLINE_QUERY_PROMO_PREFIX}{link.code}",
        "promo_text_preview": (link.promo_text or "—")[:300],
        "promo_has_text": int(bool(link.promo_text)),
        "promo_has_photo": int(bool(link.promo_photo_id)),
        "promo_buttons_info": "\n".join(lines) if lines else "—",
        "promo_btn_count": btn_count,
        "promo_btn_1_label": buttons[0]["label"] if btn_count >= 1 else "",
        "promo_btn_2_label": buttons[1]["label"] if btn_count >= 2 else "",
        "promo_btn_3_label": buttons[2]["label"] if btn_count >= 3 else "",
    }


@inject
async def promo_photo_getter(
    dialog_manager: DialogManager,
    ad_link_dao: FromDishka[AdLinkDao],
    **kwargs: Any,
) -> dict[str, Any]:
    link_id: int = dialog_manager.dialog_data.get("link_id")  # type: ignore[assignment]
    link = await ad_link_dao.get_by_id(link_id)
    return {"promo_has_photo": int(bool(link and link.promo_photo_id))}


async def promo_button_url_getter(
    dialog_manager: DialogManager, **kwargs: Any
) -> dict[str, Any]:
    return {"new_btn_label": dialog_manager.dialog_data.get("new_btn_label", "")}


async def promo_button_style_getter(
    dialog_manager: DialogManager, **kwargs: Any
) -> dict[str, Any]:
    return {"new_btn_label": dialog_manager.dialog_data.get("new_btn_label", "")}
