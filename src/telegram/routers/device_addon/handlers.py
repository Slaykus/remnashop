from dataclasses import replace
from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject
from loguru import logger

from src.application.common import Notifier
from src.application.common.dao import PaymentGatewayDao, PlanDao, SubscriptionDao
from src.application.dto import PlanSnapshotDto, PriceDetailsDto, TelegramUserDto
from src.application.services.device_pricing import one_more_device_price
from src.application.use_cases.gateways.commands.payment import CreatePayment, CreatePaymentDto
from src.core.constants import USER_KEY
from src.core.enums import PaymentGatewayType, PurchaseType
from src.telegram.states import DeviceAddon

from .getters import anchor_prices, gateway_price


def snapshot_for_devices(
    snapshot: PlanSnapshotDto, devices: int, days: int
) -> PlanSnapshotDto:
    """
    Снимок тарифа, описывающий именно эту покупку.

    Потолок устройств — новый общий, срок — остаток подписки. По первому
    проведение поймёт, сколько устройств оплачено; второй попадёт в
    описание счёта, чтобы человек в банке увидел, за какой период платит.
    """
    return replace(snapshot, device_limit=devices, duration=days)


@inject
async def on_gateway_select(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
    gateway_type: PaymentGatewayType,
    subscription_dao: FromDishka[SubscriptionDao],
    payment_gateway_dao: FromDishka[PaymentGatewayDao],
    plan_dao: FromDishka[PlanDao],
    create_payment: FromDishka[CreatePayment],
    notifier: FromDishka[Notifier],
) -> None:
    """
    Создать платёж за одно дополнительное устройство.

    Сумма считается здесь заново, а не берётся с показанного экрана:
    между показом и нажатием проходит время, а платят за оставшиеся дни.
    Пусть лучше сумма на рубль разойдётся с увиденной, чем счёт уйдёт по
    устаревшему расчёту.
    """
    user: TelegramUserDto = dialog_manager.middleware_data[USER_KEY]

    subscription = await subscription_dao.get_current(user.id)
    gateway = await payment_gateway_dao.get_by_type(gateway_type)

    if not subscription or not gateway:
        logger.error(f"{user.log} No subscription or gateway for device purchase")
        await notifier.notify_user(user, i18n_key="ntf-subscription.payment-creation-failed")
        return

    new_total = subscription.device_limit + 1
    left = subscription.days_left

    amount_rub = one_more_device_price(
        current_devices=subscription.device_limit,
        term_days=subscription.plan_snapshot.duration,
        days=left,
    )
    plan = await plan_dao.get_by_id(subscription.plan_snapshot.id)
    amount = gateway_price(gateway, amount_rub, anchor_prices(plan))

    if amount is None or amount <= 0:
        logger.error(
            f"{user.log} Refused device purchase: no price in '{gateway.currency}' "
            f"or nothing left to pay for (days_left={left})"
        )
        await notifier.notify_user(user, i18n_key="ntf-subscription.payment-creation-failed")
        return

    try:
        result = await create_payment(
            user,
            CreatePaymentDto(
                plan_snapshot=snapshot_for_devices(
                    subscription.plan_snapshot, new_total, left
                ),
                # Скидку не применяем. Разовая выдана под покупку подписки,
                # и списать её на устройство за восемьдесят рублей значило
                # бы сжечь человеку выгоду в разы большую.
                pricing=PriceDetailsDto(
                    original_amount=amount,
                    discount_percent=0,
                    final_amount=amount,
                ),
                purchase_type=PurchaseType.DEVICES,
                gateway_type=gateway_type,
            ),
        )
    except Exception:
        logger.exception(f"{user.log} Failed to create device payment")
        await notifier.notify_user(user, i18n_key="ntf-subscription.payment-creation-failed")
        return

    dialog_manager.dialog_data["payment_url"] = result.url
    dialog_manager.dialog_data["amount"] = str(amount)
    dialog_manager.dialog_data["currency"] = gateway.currency.symbol
    dialog_manager.dialog_data["new_total"] = new_total
    dialog_manager.dialog_data["days_left"] = left

    logger.info(
        f"{user.log} Created device payment '{result.id}': "
        f"{new_total} devices for {left} day(s), {amount}{gateway.currency.symbol}"
    )
    await dialog_manager.switch_to(state=DeviceAddon.CONFIRM)


async def on_cancel(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    await dialog_manager.done()
