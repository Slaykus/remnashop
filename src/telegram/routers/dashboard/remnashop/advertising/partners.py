"""
Экраны партнёров внутри раздела рекламы.

Отдельного раздела не заводим намеренно: партнёрская ссылка — это
рекламная ссылка с владельцем, и разносить их значило бы дублировать всю
воронку. Здесь только то, чего у рекламы нет: условия, баланс и выплаты.
"""

from decimal import Decimal, InvalidOperation
from typing import Any

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button as RawButton
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from src.application.common.dao import AdLinkDao
from src.application.use_cases.partner.commands.manage import (
    CreatePartner,
    CreatePartnerDto,
    ToggleLinkOwner,
    ToggleLinkOwnerDto,
    PayPartner,
    PayPartnerDto,
    UpdatePartnerTerms,
    UpdatePartnerTermsDto,
)
from src.application.use_cases.partner.queries.list import (
    GetPartnerOverview,
    GetPartners,
)
from src.core.constants import USER_KEY
from src.telegram.states import RemnashopAdvertising

_PARTNER_ID = "partner_id"


@inject
async def partners_getter(
    dialog_manager: DialogManager,
    get_partners: FromDishka[GetPartners],
    **kwargs: Any,
) -> dict[str, Any]:
    user = dialog_manager.middleware_data[USER_KEY]
    partners = await get_partners(user)
    return {
        "partners": [
            {
                "id": p.id,
                "title": f"#{p.user_id} · {p.rate_pct}%",
                "is_active": p.is_active,
            }
            for p in partners
        ],
        "is_empty": not partners,
        "count": len(partners),
    }


@inject
async def partner_view_getter(
    dialog_manager: DialogManager,
    get_overview: FromDishka[GetPartnerOverview],
    **kwargs: Any,
) -> dict[str, Any]:
    user = dialog_manager.middleware_data[USER_KEY]
    partner_id = dialog_manager.dialog_data.get(_PARTNER_ID)
    overview = await get_overview(user, partner_id) if partner_id else None

    if overview is None:
        return {"found": False}

    p, b = overview.partner, overview.balance
    return {
        "found": True,
        "name": overview.name,
        "rate_pct": str(p.rate_pct),
        "hold_days": p.hold_days,
        "min_payout": str(p.min_payout),
        "is_active": p.is_active,
        "payout_details": p.payout_details or "—",
        #
        "pending": str(b.pending),
        "available": str(b.available),
        "paid": str(b.paid),
        "total": str(b.total),
        "payments_count": b.payments_count,
        # Кнопка выплаты имеет смысл, только когда есть что платить.
        "can_pay": b.available > 0,
        "payouts_count": len(overview.payouts),
    }


async def on_partner_select(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
    item_id: int,
) -> None:
    dialog_manager.dialog_data[_PARTNER_ID] = int(item_id)
    await dialog_manager.switch_to(RemnashopAdvertising.PARTNER_VIEW)


@inject
async def on_partner_add_input(
    message: Message,
    widget: Any,
    dialog_manager: DialogManager,
    create_partner: FromDishka[CreatePartner],
) -> None:
    user = dialog_manager.middleware_data[USER_KEY]
    raw = (message.text or "").strip()
    if not raw.lstrip("-").isdigit():
        await message.answer("Нужен telegram id числом.")
        return

    partner = await create_partner(user, CreatePartnerDto(telegram_id=int(raw)))
    if partner is None:
        await message.answer("Пользователь с таким id в боте не найден.")
        return

    dialog_manager.dialog_data[_PARTNER_ID] = partner.id
    await dialog_manager.switch_to(RemnashopAdvertising.PARTNER_VIEW)


def _parse_decimal(raw: str) -> Decimal | None:
    try:
        value = Decimal(raw.strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        return None
    return value if value >= 0 else None


@inject
async def on_rate_input(
    message: Message,
    widget: Any,
    dialog_manager: DialogManager,
    update_terms: FromDishka[UpdatePartnerTerms],
) -> None:
    value = _parse_decimal(message.text or "")
    # Ставка выше сотни означала бы платить больше, чем получили.
    if value is None or value > 100:
        await message.answer("Ставка — число от 0 до 100.")
        return
    await _apply(dialog_manager, update_terms, rate_pct=value)


@inject
async def on_hold_input(
    message: Message,
    widget: Any,
    dialog_manager: DialogManager,
    update_terms: FromDishka[UpdatePartnerTerms],
) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit() or int(raw) > 365:
        await message.answer("Срок удержания — целое число дней, не больше 365.")
        return
    await _apply(dialog_manager, update_terms, hold_days=int(raw))


@inject
async def on_min_payout_input(
    message: Message,
    widget: Any,
    dialog_manager: DialogManager,
    update_terms: FromDishka[UpdatePartnerTerms],
) -> None:
    value = _parse_decimal(message.text or "")
    if value is None:
        await message.answer("Минимальная выплата — неотрицательное число.")
        return
    await _apply(dialog_manager, update_terms, min_payout=value)


async def _apply(
    dialog_manager: DialogManager,
    update_terms: UpdatePartnerTerms,
    **changes: Any,
) -> None:
    user = dialog_manager.middleware_data[USER_KEY]
    partner_id = dialog_manager.dialog_data.get(_PARTNER_ID)
    if not partner_id:
        return
    await update_terms(user, UpdatePartnerTermsDto(partner_id=int(partner_id), **changes))
    await dialog_manager.switch_to(RemnashopAdvertising.PARTNER_VIEW)


@inject
async def on_partner_toggle_active(
    callback: CallbackQuery,
    button: RawButton,
    dialog_manager: DialogManager,
    get_overview: FromDishka[GetPartnerOverview],
    update_terms: FromDishka[UpdatePartnerTerms],
) -> None:
    user = dialog_manager.middleware_data[USER_KEY]
    partner_id = dialog_manager.dialog_data.get(_PARTNER_ID)
    if not partner_id:
        return
    overview = await get_overview(user, int(partner_id))
    if overview is None:
        return
    # Отключение не стирает начисленное: партнёр перестаёт получать новое,
    # но заработанное остаётся к выплате.
    await update_terms(
        user,
        UpdatePartnerTermsDto(partner_id=int(partner_id), is_active=not overview.partner.is_active),
    )
    # Карточку надо перерисовать явно: без этого человек видит прежнее
    # состояние и решает, что кнопка не сработала.
    await dialog_manager.show()


@inject
async def on_pay(
    callback: CallbackQuery,
    button: RawButton,
    dialog_manager: DialogManager,
    pay_partner: FromDishka[PayPartner],
) -> None:
    user = dialog_manager.middleware_data[USER_KEY]
    partner_id = dialog_manager.dialog_data.get(_PARTNER_ID)
    if not partner_id:
        return

    payout = await pay_partner(user, PayPartnerDto(partner_id=int(partner_id)))
    if payout is None:
        await callback.answer("Платить нечего или сумма ниже минимальной.", show_alert=True)
        return
    await callback.answer(
        f"Оформлена выплата {payout.amount} ₽ по {payout.earnings_count} начислениям.",
        show_alert=True,
    )


@inject
async def partner_links_getter(
    dialog_manager: DialogManager,
    get_overview: FromDishka[GetPartnerOverview],
    ad_link_dao: FromDishka[AdLinkDao],
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Все рекламные ссылки с отметкой, чьи они.

    Показываем и чужие тоже — иначе непонятно, почему нужной ссылки нет в
    списке. Занятые видно сразу, и случайно перехватить их нельзя: нажатие
    на чужую ничего не делает.
    """
    user = dialog_manager.middleware_data[USER_KEY]
    partner_id = dialog_manager.dialog_data.get(_PARTNER_ID)
    overview = await get_overview(user, int(partner_id)) if partner_id else None
    if overview is None:
        return {"links": [], "is_empty": True}

    owner_id = overview.partner.user_id
    links = []
    for ln in await ad_link_dao.get_all():
        if ln.owner_user_id == owner_id:
            mark = "✅"
        elif ln.owner_user_id is None:
            mark = "▫️"
        else:
            mark = "🔒"
        links.append(
            {
                "id": ln.id,
                "title": f"{mark} {ln.name} ({ln.code})",
                "busy": ln.owner_user_id is not None and ln.owner_user_id != owner_id,
            }
        )
    return {"links": links, "is_empty": not links, "name": overview.name}


@inject
async def on_link_toggle(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
    item_id: int,
    toggle_owner: FromDishka[ToggleLinkOwner],
) -> None:
    user = dialog_manager.middleware_data[USER_KEY]
    partner_id = dialog_manager.dialog_data.get(_PARTNER_ID)
    if not partner_id:
        return

    attached = await toggle_owner(
        user, ToggleLinkOwnerDto(link_id=int(item_id), partner_id=int(partner_id))
    )
    await callback.answer("Ссылка закреплена" if attached else "Закрепление снято")
    await dialog_manager.show()
