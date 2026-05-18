from aiogram_dialog import Dialog, StartMode, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Row, ScrollingGroup, Select, SwitchTo
from aiogram_dialog.widgets.text import Format
from magic_filter import F

from src.core.enums import BannerName
from src.telegram.keyboards import main_menu_button
from src.telegram.states import DashboardRemnashop, RemnashopAdvertising
from src.telegram.widgets import Banner, I18nFormat, IgnoreUpdate

from .getters import (
    confirm_delete_getter,
    create_code_getter,
    create_name_getter,
    edit_getter,
    list_getter,
    view_getter,
)
from .handlers import (
    on_create_code_input,
    on_create_name_input,
    on_delete_confirm,
    on_edit_bonus_days_input,
    on_edit_bonus_discount_input,
    on_edit_bonus_points_input,
    on_edit_name_input,
    on_link_select,
    on_toggle_active,
)

ad_list = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-advertising-list"),
    ScrollingGroup(
        Select(
            text=Format("{item[name]} ({item[code]}) — {item[clicks_count]} кл."),
            id="link_select",
            item_id_getter=lambda item: item["id"],
            items="links",
            type_factory=int,
            on_click=on_link_select,
        ),
        id="links_scroll",
        width=1,
        height=8,
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-advertising.create"),
            id="create",
            state=RemnashopAdvertising.CREATE_NAME,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=DashboardRemnashop.MAIN,
            mode=StartMode.RESET_STACK,
        ),
        *main_menu_button,
    ),
    IgnoreUpdate(),
    state=RemnashopAdvertising.LIST,
    getter=list_getter,
)

ad_view = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-advertising-view"),
    Row(
        Button(
            text=I18nFormat("btn-advertising.toggle-active"),
            id="toggle_active",
            on_click=on_toggle_active,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-advertising.edit-name"),
            id="edit_name",
            state=RemnashopAdvertising.EDIT_NAME,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-advertising.bonus-points"),
            id="edit_bonus_points",
            state=RemnashopAdvertising.EDIT_BONUS_POINTS,
        ),
        SwitchTo(
            text=I18nFormat("btn-advertising.bonus-days"),
            id="edit_bonus_days",
            state=RemnashopAdvertising.EDIT_BONUS_DAYS,
        ),
        SwitchTo(
            text=I18nFormat("btn-advertising.bonus-discount"),
            id="edit_bonus_discount",
            state=RemnashopAdvertising.EDIT_BONUS_DISCOUNT,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-advertising.delete"),
            id="delete",
            state=RemnashopAdvertising.CONFIRM_DELETE,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=RemnashopAdvertising.LIST,
        ),
        *main_menu_button,
    ),
    IgnoreUpdate(),
    state=RemnashopAdvertising.VIEW,
    getter=view_getter,
)

ad_create_name = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-advertising-create-name"),
    MessageInput(func=on_create_name_input),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=RemnashopAdvertising.LIST,
        ),
    ),
    IgnoreUpdate(),
    state=RemnashopAdvertising.CREATE_NAME,
    getter=create_name_getter,
)

ad_create_code = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-advertising-create-code"),
    MessageInput(func=on_create_code_input),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=RemnashopAdvertising.CREATE_NAME,
        ),
    ),
    IgnoreUpdate(),
    state=RemnashopAdvertising.CREATE_CODE,
    getter=create_code_getter,
)

ad_edit_name = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-advertising-edit-name"),
    MessageInput(func=on_edit_name_input),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=RemnashopAdvertising.VIEW,
        ),
    ),
    IgnoreUpdate(),
    state=RemnashopAdvertising.EDIT_NAME,
    getter=edit_getter,
)

ad_edit_bonus_points = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-advertising-edit-bonus-points"),
    MessageInput(func=on_edit_bonus_points_input),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=RemnashopAdvertising.VIEW,
        ),
    ),
    IgnoreUpdate(),
    state=RemnashopAdvertising.EDIT_BONUS_POINTS,
    getter=edit_getter,
)

ad_edit_bonus_days = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-advertising-edit-bonus-days"),
    MessageInput(func=on_edit_bonus_days_input),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=RemnashopAdvertising.VIEW,
        ),
    ),
    IgnoreUpdate(),
    state=RemnashopAdvertising.EDIT_BONUS_DAYS,
    getter=edit_getter,
)

ad_edit_bonus_discount = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-advertising-edit-bonus-discount"),
    MessageInput(func=on_edit_bonus_discount_input),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=RemnashopAdvertising.VIEW,
        ),
    ),
    IgnoreUpdate(),
    state=RemnashopAdvertising.EDIT_BONUS_DISCOUNT,
    getter=edit_getter,
)

ad_confirm_delete = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-advertising-confirm-delete"),
    Row(
        Button(
            text=I18nFormat("btn-advertising.delete-confirm"),
            id="delete_confirm",
            on_click=on_delete_confirm,
        ),
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=RemnashopAdvertising.VIEW,
        ),
    ),
    IgnoreUpdate(),
    state=RemnashopAdvertising.CONFIRM_DELETE,
    getter=confirm_delete_getter,
)

router = Dialog(
    ad_list,
    ad_view,
    ad_create_name,
    ad_create_code,
    ad_edit_name,
    ad_edit_bonus_points,
    ad_edit_bonus_days,
    ad_edit_bonus_discount,
    ad_confirm_delete,
)
