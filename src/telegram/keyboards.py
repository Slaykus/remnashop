from typing import Final

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram_dialog import StartMode
from aiogram_dialog.widgets.kbd import Row, Start, Url, WebApp
from aiogram_dialog.widgets.text import Format
from magic_filter import F

from src.core.constants import GOTO_PREFIX, PAYMENT_PREFIX, REPOSITORY, T_ME
from src.core.enums import PurchaseType
from src.telegram.states import DashboardUser, MainMenu, Subscription
from src.telegram.utils import username_to_url
from src.telegram.widgets import I18nFormat

CALLBACK_CHANNEL_CONFIRM: Final[str] = "channel_confirm"
CALLBACK_RULES_ACCEPT: Final[str] = "rules_accept"

connect_buttons = (
    WebApp(
        text=I18nFormat("btn-menu.connect"),
        url=Format("{connection_url}"),
        id="connect_miniapp",
        when=F["is_mini_app"] & F["connectable"],
    ),
    Url(
        text=I18nFormat("btn-menu.connect"),
        url=Format("{connection_url}"),
        id="connect_sub_page",
        when=~F["is_mini_app"] & F["connectable"],
    ),
)

main_menu_button = (
    Start(
        text=I18nFormat("btn-back.menu"),
        id="back_main_menu",
        state=MainMenu.MAIN,
        mode=StartMode.RESET_STACK,
    ),
)

back_main_menu_button = (
    Row(
        Start(
            text=I18nFormat("btn-back.menu-return"),
            id="back_main_menu",
            state=MainMenu.MAIN,
            mode=StartMode.RESET_STACK,
        ),
    ),
)


def get_goto_buttons(is_referral_enable: bool, url: str) -> list[InlineKeyboardButton]:
    buttons = [
        InlineKeyboardButton(
            text="btn-goto.contact-support",
            url=url,
        ),
        InlineKeyboardButton(
            text="btn-goto.subscription",
            callback_data=f"{GOTO_PREFIX}{Subscription.MAIN.state}",
        ),
        InlineKeyboardButton(
            text="btn-goto.promocode",
            callback_data=f"{GOTO_PREFIX}{Subscription.PROMOCODE.state}",
        ),
    ]

    if is_referral_enable:
        buttons.append(
            InlineKeyboardButton(
                text="btn-goto.invite",
                callback_data=f"{GOTO_PREFIX}{MainMenu.INVITE.state}",
            )
        )

    return buttons


def get_renew_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="btn-goto.subscription-renew",
            callback_data=f"{GOTO_PREFIX}{PAYMENT_PREFIX}{PurchaseType.RENEW}",
        ),
    )
    return builder.as_markup()


def get_buy_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="btn-goto.subscription",
            callback_data=f"{GOTO_PREFIX}{PAYMENT_PREFIX}{PurchaseType.NEW}",
        ),
    )
    return builder.as_markup()


def get_channel_keyboard(channel_link: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="btn-requirement.channel-join",
            url=channel_link,
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="btn-requirement.channel-confirm",
            callback_data=CALLBACK_CHANNEL_CONFIRM,
        ),
    )
    return builder.as_markup()


def get_rules_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="btn-requirement.rules-accept",
            callback_data=CALLBACK_RULES_ACCEPT,
        ),
    )
    return builder.as_markup()


def get_contact_support_keyboard(username: str, text: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="btn-goto.contact-support",
            url=username_to_url(username, text),
        ),
    )
    return builder.as_markup()


def get_remnashop_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="btn-remnashop-info.github",
            url=REPOSITORY,
        ),
        InlineKeyboardButton(
            text="btn-remnashop-info.telegram",
            url=f"{T_ME}remna_shop",
        ),
    )

    builder.row(
        InlineKeyboardButton(
            text="btn-remnashop-info.donate",
            url="https://yookassa.ru/my/i/Z8AkHJ_F9sO_/l",
        )
    )

    return builder.as_markup()


def get_remnashop_update_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="btn-remnashop-info.release-latest",
            url=f"{REPOSITORY}/releases/latest",
        ),
        InlineKeyboardButton(
            text="btn-remnashop-info.how-upgrade",
            url=f"{REPOSITORY}?tab=readme-ov-file#step-5--how-to-upgrade",
        ),
    )

    return builder.as_markup()


def get_user_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="btn-goto.user-profile",
            callback_data=f"{GOTO_PREFIX}{DashboardUser.MAIN.state}:{telegram_id}",
        ),
    )

    return builder.as_markup()
