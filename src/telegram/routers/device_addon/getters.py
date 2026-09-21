from math import ceil
from typing import Any, Optional

from aiogram_dialog import DialogManager
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from src.application.common import Remnawave, TranslatorRunner
from src.application.common.dao import PaymentGatewayDao, PlanDao, SubscriptionDao
from src.application.dto import PaymentGatewayDto, PlanDto, SubscriptionDto, TelegramUserDto
from src.application.services.device_pricing import (
    MAX_ADDON_DEVICES,
    extra_devices_price,
    price_in_currency,
)
from src.core.enums import Currency
from src.core.exceptions import PriceNotFoundError
from src.core.utils.i18n_helpers import i18n_format_days
from src.core.utils.time import datetime_now

# Сколько знаков после запятой у суммы в каждой валюте. Звёзды и рубли
# целые, доллары — с копейками.
_DECIMALS: dict[Currency, int] = {
    Currency.RUB: 0,
    Currency.USD: 2,
    Currency.XTR: 0,
}

# Месячная цена тарифа — тот якорь, от которого считается курс. Своих цен
# в валютах у устройств нет, а у тарифов есть, и отношение между валютами
# по всему прайсу одинаковое.
_ANCHOR_DAYS: int = 30


def _gateway_title(i18n: TranslatorRunner, gateway: PaymentGatewayDto) -> str:
    """То же, что в диалоге подписки: имя из настроек, иначе из перевода."""
    if gateway.settings and gateway.settings.display_name:
        return gateway.settings.display_name

    return i18n.get("gateway-type", gateway_type=gateway.type)


def days_left(subscription: SubscriptionDto) -> int:
    """Сколько дней ещё оплачено. Ровно за них и берём деньги."""
    if not subscription.expire_at:
        return 0
    return max(0, ceil((subscription.expire_at - datetime_now()).total_seconds() / 86400))


def anchor_prices(plan: Optional[PlanDto]) -> Optional[tuple[Any, Any]]:
    """Месячные цены тарифа в рублях — от них считается курс."""
    if not plan:
        return None
    duration = plan.get_duration(_ANCHOR_DAYS)
    if not duration:
        return None
    try:
        return duration, duration.get_price(Currency.RUB)
    except PriceNotFoundError:
        return None


def gateway_price(
    gateway: PaymentGatewayDto,
    amount_rub: Any,
    anchor: Optional[tuple[Any, Any]],
) -> Optional[Any]:
    """
    Цена докупки в валюте шлюза.

    Пусто означает, что у тарифа нет цены в этой валюте и пересчитывать
    не от чего. Такой шлюз просто не показываем: лучше не предложить
    способ оплаты, чем назвать цену наугад.
    """
    if gateway.currency == Currency.RUB:
        return amount_rub
    if anchor is None:
        return None

    duration, anchor_rub = anchor
    try:
        anchor_in_currency = duration.get_price(gateway.currency)
    except PriceNotFoundError:
        return None

    return price_in_currency(
        amount_rub,
        anchor_rub,
        anchor_in_currency,
        _DECIMALS.get(gateway.currency, 2),
    )


@inject
async def addon_getter(
    dialog_manager: DialogManager,
    user: TelegramUserDto,
    i18n: FromDishka[TranslatorRunner],
    subscription_dao: FromDishka[SubscriptionDao],
    payment_gateway_dao: FromDishka[PaymentGatewayDao],
    plan_dao: FromDishka[PlanDao],
    remnawave: FromDishka[Remnawave],
    **kwargs: Any,
) -> dict[str, Any]:
    subscription = await subscription_dao.get_current(user.id)
    if not subscription:
        raise ValueError(f"Current subscription for user '{user.telegram_id}' not found")

    connected = len(await remnawave.get_devices(subscription.user_remna_id))
    current_limit = subscription.device_limit
    new_total = current_limit + 1
    left = days_left(subscription)

    amount_rub = extra_devices_price(
        total_devices=new_total,
        term_days=subscription.plan_snapshot.duration,
        days=left,
    )

    plan = await plan_dao.get_by_id(subscription.plan_snapshot.id)
    anchor = anchor_prices(plan)

    payment_methods = []
    for gateway in await payment_gateway_dao.get_active():
        price = gateway_price(gateway, amount_rub, anchor)
        if price is None:
            continue
        payment_methods.append(
            {
                "gateway_type": gateway.type,
                "gateway_title": _gateway_title(i18n, gateway),
                "amount": price,
                "currency": gateway.currency.symbol,
            }
        )

    # Месячная цена того же набора — её человек увидит при продлении, и
    # узнать о ней он должен до оплаты, а не через месяц при списании.
    monthly_rub = extra_devices_price(total_devices=new_total, term_days=30)

    dialog_manager.dialog_data["new_total"] = new_total
    dialog_manager.dialog_data["days_left"] = left

    # Ветку выбираем готовой строкой, а не условием в переводе: селекторы
    # сопоставляют ключи как строки, и булево в ветку [true] не попадает.
    if new_total > MAX_ADDON_DEVICES:
        state = "CEILING"
    elif not payment_methods:
        state = "NO_METHODS"
    elif left <= 0 or amount_rub <= 0:
        state = "NOTHING_TO_PAY"
    else:
        state = "OK"

    days_key, days_kwargs = i18n_format_days(left)

    return {
        "addon_state": state,
        "connected": connected,
        "current_limit": current_limit,
        "new_total": new_total,
        "max_devices": MAX_ADDON_DEVICES,
        "days_left": left,
        "days_left_text": i18n.get(days_key, **days_kwargs),
        "expire_at": subscription.expire_at.strftime("%d.%m.%Y"),
        "amount_rub": amount_rub,
        "monthly_rub": monthly_rub,
        "payment_methods": payment_methods,
        "has_methods": len(payment_methods) > 0,
        "can_pay": int(state == "OK"),
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
