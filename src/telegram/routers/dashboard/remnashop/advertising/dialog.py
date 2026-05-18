from aiogram.enums import ButtonStyle, ContentType
from aiogram_dialog import Dialog, StartMode, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button, Row, ScrollingGroup, Select, Start, SwitchTo
from aiogram_dialog.widgets.style import Style
from aiogram_dialog.widgets.text import Format
from magic_filter import F

from src.core.enums import BannerName
from src.telegram.keyboards import main_menu_button
from src.telegram.states import DashboardRemnashop, RemnashopAdvertising
from src.telegram.widgets import Banner, I18nFormat, IgnoreUpdate

from .getters import (
    analytics_getter,
    comparison_getter,
    confirm_delete_getter,
    create_code_getter,
    create_name_getter,
    edit_getter,
    list_getter,
    promo_button_style_getter,
    promo_button_url_getter,
    promo_getter,
    promo_photo_getter,
    view_getter,
)
from .handlers import (
    on_create_code_input,
    on_create_name_input,
    on_delete_confirm,
    on_delete_promo_button,
    on_edit_bonus_days_input,
    on_edit_bonus_discount_input,
    on_edit_bonus_points_input,
    on_edit_name_input,
    on_link_select,
    on_promo_button_label_input,
    on_promo_button_url_input,
    on_promo_remove_photo,
    on_promo_set_photo,
    on_promo_set_style,
    on_promo_set_text,
    on_promo_use_ad_url,
    on_send_comparison_chart,
    on_send_funnel_chart,
    on_send_promo_preview,
    on_send_trend_chart,
    on_set_analytics_period,
    on_set_comparison_sort,
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
        SwitchTo(
            text=I18nFormat("btn-advertising.comparison"),
            id="comparison",
            state=RemnashopAdvertising.COMPARISON,
        ),
    ),
    Row(
        Start(
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
            text=I18nFormat("btn-advertising.promo"),
            id="promo",
            state=RemnashopAdvertising.PROMO,
        ),
        SwitchTo(
            text=I18nFormat("btn-advertising.analytics"),
            id="analytics",
            state=RemnashopAdvertising.ANALYTICS,
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

ad_promo = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-advertising-promo"),
    Row(
        SwitchTo(
            text=I18nFormat("btn-advertising.promo-edit-text"),
            id="promo_edit_text",
            state=RemnashopAdvertising.EDIT_PROMO_TEXT,
        ),
        SwitchTo(
            text=I18nFormat("btn-advertising.promo-photo"),
            id="promo_photo",
            state=RemnashopAdvertising.EDIT_PROMO_PHOTO,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-advertising.promo-add-button"),
            id="promo_add_btn",
            state=RemnashopAdvertising.PROMO_BUTTON_LABEL,
            when=F["promo_btn_count"] < 3,
        ),
    ),
    Row(
        Button(
            text=Format("🗑 {promo_btn_1_label}"),
            id="del_btn_0",
            on_click=on_delete_promo_button,
            when=F["promo_btn_count"] >= 1,
        ),
        Button(
            text=Format("🗑 {promo_btn_2_label}"),
            id="del_btn_1",
            on_click=on_delete_promo_button,
            when=F["promo_btn_count"] >= 2,
        ),
        Button(
            text=Format("🗑 {promo_btn_3_label}"),
            id="del_btn_2",
            on_click=on_delete_promo_button,
            when=F["promo_btn_count"] >= 3,
        ),
    ),
    Row(
        Button(
            text=I18nFormat("btn-advertising.promo-preview"),
            id="promo_preview",
            on_click=on_send_promo_preview,
            when=F["promo_has_text"],
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=RemnashopAdvertising.VIEW,
        ),
    ),
    IgnoreUpdate(),
    state=RemnashopAdvertising.PROMO,
    getter=promo_getter,
)

ad_edit_promo_text = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-advertising-promo-edit-text"),
    MessageInput(func=on_promo_set_text),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=RemnashopAdvertising.PROMO,
        ),
    ),
    IgnoreUpdate(),
    state=RemnashopAdvertising.EDIT_PROMO_TEXT,
    getter=edit_getter,
)

ad_edit_promo_photo = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-advertising-promo-edit-photo"),
    MessageInput(func=on_promo_set_photo, content_types=[ContentType.PHOTO]),
    Row(
        Button(
            text=I18nFormat("btn-advertising.promo-remove-photo"),
            id="remove_photo",
            on_click=on_promo_remove_photo,
            when=F["promo_has_photo"],
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=RemnashopAdvertising.PROMO,
        ),
    ),
    IgnoreUpdate(),
    state=RemnashopAdvertising.EDIT_PROMO_PHOTO,
    getter=promo_photo_getter,
)

ad_promo_button_label = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-advertising-promo-button-label"),
    MessageInput(func=on_promo_button_label_input),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=RemnashopAdvertising.PROMO,
        ),
    ),
    IgnoreUpdate(),
    state=RemnashopAdvertising.PROMO_BUTTON_LABEL,
    getter=edit_getter,
)

ad_promo_button_url = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-advertising-promo-button-url"),
    MessageInput(func=on_promo_button_url_input),
    Row(
        Button(
            text=I18nFormat("btn-advertising.promo-use-ad-url"),
            id="use_ad_url",
            on_click=on_promo_use_ad_url,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=RemnashopAdvertising.PROMO_BUTTON_LABEL,
        ),
    ),
    IgnoreUpdate(),
    state=RemnashopAdvertising.PROMO_BUTTON_URL,
    getter=promo_button_url_getter,
)

ad_promo_button_style = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-advertising-promo-button-style"),
    Row(
        Button(
            text=I18nFormat("btn-advertising.promo-style-default"),
            id="style_default",
            on_click=on_promo_set_style,
        ),
        Button(
            text=I18nFormat("btn-advertising.promo-style-primary"),
            id="style_primary",
            on_click=on_promo_set_style,
            style=Style(ButtonStyle.PRIMARY),
        ),
        Button(
            text=I18nFormat("btn-advertising.promo-style-success"),
            id="style_success",
            on_click=on_promo_set_style,
            style=Style(ButtonStyle.SUCCESS),
        ),
        Button(
            text=I18nFormat("btn-advertising.promo-style-danger"),
            id="style_danger",
            on_click=on_promo_set_style,
            style=Style(ButtonStyle.DANGER),
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=RemnashopAdvertising.PROMO_BUTTON_URL,
        ),
    ),
    IgnoreUpdate(),
    state=RemnashopAdvertising.PROMO_BUTTON_STYLE,
    getter=promo_button_style_getter,
)

ad_analytics = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-advertising-analytics"),
    Row(
        Button(
            text=I18nFormat("btn-advertising.analytics-period-7"),
            id="period_7",
            on_click=on_set_analytics_period,
        ),
        Button(
            text=I18nFormat("btn-advertising.analytics-period-30"),
            id="period_30",
            on_click=on_set_analytics_period,
        ),
        Button(
            text=I18nFormat("btn-advertising.analytics-period-0"),
            id="period_0",
            on_click=on_set_analytics_period,
        ),
    ),
    Row(
        Button(
            text=I18nFormat("btn-advertising.analytics-trend"),
            id="chart_trend",
            on_click=on_send_trend_chart,
        ),
        Button(
            text=I18nFormat("btn-advertising.analytics-funnel"),
            id="chart_funnel",
            on_click=on_send_funnel_chart,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=RemnashopAdvertising.VIEW,
        ),
    ),
    IgnoreUpdate(),
    state=RemnashopAdvertising.ANALYTICS,
    getter=analytics_getter,
)

ad_comparison = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-advertising-comparison"),
    Row(
        Button(
            text=I18nFormat("btn-advertising.comparison-sort-revenue"),
            id="sort_revenue",
            on_click=on_set_comparison_sort,
        ),
        Button(
            text=I18nFormat("btn-advertising.comparison-sort-conversion"),
            id="sort_conversion",
            on_click=on_set_comparison_sort,
        ),
        Button(
            text=I18nFormat("btn-advertising.comparison-sort-clicks"),
            id="sort_clicks",
            on_click=on_set_comparison_sort,
        ),
    ),
    Row(
        Button(
            text=I18nFormat("btn-advertising.comparison-chart"),
            id="comparison_chart",
            on_click=on_send_comparison_chart,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=RemnashopAdvertising.LIST,
        ),
    ),
    IgnoreUpdate(),
    state=RemnashopAdvertising.COMPARISON,
    getter=comparison_getter,
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
    ad_promo,
    ad_edit_promo_text,
    ad_edit_promo_photo,
    ad_promo_button_label,
    ad_promo_button_url,
    ad_promo_button_style,
    ad_analytics,
    ad_comparison,
)
