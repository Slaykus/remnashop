from aiogram.enums import ButtonStyle
from aiogram_dialog import Dialog, Window
from aiogram_dialog.widgets.style import Style
from aiogram_dialog.widgets.text import Format
from magic_filter import F

from src.core.enums import BannerName, PaymentGatewayType
from src.telegram.states import DeviceAddon
from src.telegram.widgets import Banner, I18nFormat
from src.telegram.widgets.kbd import Button, Column, Row, Select, Url

from .getters import addon_confirm_getter, addon_getter
from .handlers import on_cancel, on_gateway_select

main = Window(
    Banner(BannerName.DEVICES),
    I18nFormat("msg-device-addon"),
    Column(
        # Список читается из таблицы шлюзов тем же запросом, что и в
        # подписке, поэтому включение и выключение способов оплаты из
        # админки работает здесь так же.
        Select(
            text=I18nFormat(
                "btn-device-addon.pay-with",
                gateway_title=F["item"]["gateway_title"],
                amount=F["item"]["amount"],
                currency=F["item"]["currency"],
            ),
            id="device_addon_gateway",
            item_id_getter=lambda item: item["gateway_type"],
            items="payment_methods",
            type_factory=PaymentGatewayType,
            on_click=on_gateway_select,
            style=Style(ButtonStyle.SUCCESS),
            when=F["can_pay"] == 1,
        ),
    ),
    Row(
        Button(
            text=I18nFormat("btn-device-addon.cancel"),
            id="device_addon_cancel",
            on_click=on_cancel,
        ),
    ),
    state=DeviceAddon.MAIN,
    getter=addon_getter,
)

confirm = Window(
    Banner(BannerName.DEVICES),
    I18nFormat("msg-device-addon-confirm"),
    Row(
        Url(
            text=I18nFormat(
                "btn-device-addon.pay",
                amount=F["amount"],
                currency=F["currency"],
            ),
            url=Format("{url}"),
            when=F["url"],
            style=Style(ButtonStyle.SUCCESS),
        ),
    ),
    Row(
        Button(
            text=I18nFormat("btn-device-addon.cancel"),
            id="device_addon_confirm_cancel",
            on_click=on_cancel,
        ),
    ),
    state=DeviceAddon.CONFIRM,
    getter=addon_confirm_getter,
)

router = Dialog(main, confirm)
