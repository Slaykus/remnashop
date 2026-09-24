from typing import Any

from aiogram.types import CallbackQuery
from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.kbd import Button
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject
from loguru import logger

from src.application.common import Notifier
from src.application.dto import TelegramUserDto
from src.application.use_cases.subscription.commands.add_device import (
    CreateDeviceAddonPayment,
    CreateDeviceAddonPaymentDto,
    DeviceAddonError,
)
from src.core.constants import USER_KEY
from src.core.enums import PaymentGatewayType
from src.telegram.states import DeviceAddon


@inject
async def on_gateway_select(
    callback: CallbackQuery,
    widget: Any,
    dialog_manager: DialogManager,
    gateway_type: PaymentGatewayType,
    create_addon_payment: FromDishka[CreateDeviceAddonPayment],
    notifier: FromDishka[Notifier],
) -> None:
    """
    Создать счёт на одно дополнительное устройство.

    Сумму считает сценарий, а не экран: между показом цены и нажатием
    проходит время, а платят за оставшиеся дни.
    """
    user: TelegramUserDto = dialog_manager.middleware_data[USER_KEY]

    try:
        result = await create_addon_payment(
            user, CreateDeviceAddonPaymentDto(gateway_type=gateway_type)
        )
    except DeviceAddonError as error:
        logger.warning(f"{user.log} Device purchase refused: {error}")
        await notifier.notify_user(user, i18n_key="ntf-subscription.payment-creation-failed")
        return
    except Exception:
        logger.exception(f"{user.log} Failed to create device payment")
        await notifier.notify_user(user, i18n_key="ntf-subscription.payment-creation-failed")
        return

    # Показываем ровно ту сумму, на которую выставлен счёт: считать её
    # заново для экрана значило бы однажды показать одно, а списать другое.
    dialog_manager.dialog_data["payment_url"] = result.payment_url
    dialog_manager.dialog_data["amount"] = str(result.amount)
    dialog_manager.dialog_data["currency"] = result.currency
    dialog_manager.dialog_data["new_total"] = result.new_total
    dialog_manager.dialog_data["days_left"] = result.days_left
    await dialog_manager.switch_to(state=DeviceAddon.CONFIRM)


async def on_cancel(
    callback: CallbackQuery,
    button: Button,
    dialog_manager: DialogManager,
) -> None:
    await dialog_manager.done()
