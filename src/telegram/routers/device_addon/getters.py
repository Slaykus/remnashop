from typing import Any

from aiogram_dialog import DialogManager
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from src.application.common import TranslatorRunner
from src.application.common.dao import PaymentGatewayDao
from src.application.dto import PaymentGatewayDto, TelegramUserDto
from src.application.use_cases.subscription.commands.add_device import GetDeviceAddonOffer
from src.core.utils.i18n_helpers import i18n_format_days


def _gateway_title(i18n: TranslatorRunner, gateway: PaymentGatewayDto) -> str:
    """То же, что в диалоге подписки: имя из настроек, иначе из перевода."""
    if gateway.settings and gateway.settings.display_name:
        return gateway.settings.display_name

    return i18n.get("gateway-type", gateway_type=gateway.type)


@inject
async def addon_getter(
    dialog_manager: DialogManager,
    user: TelegramUserDto,
    i18n: FromDishka[TranslatorRunner],
    payment_gateway_dao: FromDishka[PaymentGatewayDao],
    get_offer: FromDishka[GetDeviceAddonOffer],
    **kwargs: Any,
) -> dict[str, Any]:
    # Считает сценарий, а не экран: то же предложение отдаётся сайту, и
    # два расчёта однажды разошлись бы.
    offer = await get_offer(user)

    titles = {
        gateway.type: _gateway_title(i18n, gateway)
        for gateway in await payment_gateway_dao.get_active()
    }
    payment_methods = [
        {
            "gateway_type": method.gateway_type,
            "gateway_title": titles.get(method.gateway_type, method.gateway_type),
            "amount": method.amount,
            "currency": method.currency,
        }
        for method in offer.methods
    ]

    dialog_manager.dialog_data["new_total"] = offer.new_total
    dialog_manager.dialog_data["days_left"] = offer.days_left

    days_key, days_kwargs = i18n_format_days(offer.days_left)

    return {
        # Ветку выбираем готовой строкой: селекторы в переводах сопоставляют
        # ключи как строки, и булево в ветку [true] не попадает.
        "addon_state": offer.state,
        "current_limit": offer.current_limit,
        "new_total": offer.new_total,
        "max_devices": offer.max_devices,
        "days_left": offer.days_left,
        "days_left_text": i18n.get(days_key, **days_kwargs),
        "expire_at": offer.expire_at.strftime("%d.%m.%Y") if offer.expire_at else "—",
        "amount_rub": offer.amount_rub,
        "monthly_rub": offer.monthly_rub,
        "monthly_total_rub": offer.monthly_total_rub,
        "payment_methods": payment_methods,
        "has_methods": len(payment_methods) > 0,
        "can_pay": int(offer.can_pay),
    }


async def addon_confirm_getter(
    dialog_manager: DialogManager,
    **kwargs: Any,
) -> dict[str, Any]:
    return {
        "new_total": dialog_manager.dialog_data.get("new_total", 0),
        "days_left": dialog_manager.dialog_data.get("days_left", 0),
        "amount": dialog_manager.dialog_data.get("amount", 0),
        "currency": dialog_manager.dialog_data.get("currency", ""),
        "url": dialog_manager.dialog_data.get("payment_url"),
    }
