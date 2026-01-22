from typing import Any

from aiogram_dialog import DialogManager
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from src.application.common import TranslatorRunner
from src.application.dto import UserDto
from src.application.use_cases.menu import GetMenuData
from src.core.config import AppConfig
from src.core.exceptions import MenuRenderError
from src.core.utils.i18n_helpers import (
    i18n_format_device_limit,
    i18n_format_expire_time,
    i18n_format_traffic_limit,
)
from src.core.utils.time import get_traffic_reset_delta
from src.telegram.utils import username_to_url


@inject
async def menu_getter(
    dialog_manager: DialogManager,
    config: AppConfig,
    user: UserDto,
    i18n: FromDishka[TranslatorRunner],
    get_menu_data: FromDishka[GetMenuData],
    **kwargs: Any,
) -> dict[str, Any]:
    try:
        menu_data = await get_menu_data(user)

        support_username = config.bot.support_username.get_secret_value()
        support_url = username_to_url(support_username, i18n.get("message.help"))

        data: dict[str, Any] = {
            # user
            "telegram_id": user.telegram_id,
            "name": user.name,
            "personal_discount": user.personal_discount,
            # ui / config
            "is_mini_app": config.bot.is_mini_app,
            "support_url": support_url,
            # referral
            "referral_enabled": menu_data.is_referral_enabled,
            "invite_url": i18n.get("message.referral-invite", url=menu_data.referral_url),
            # defaults
            "has_subscription": False,
            "connectable": False,
            "trial_available": False,
            "has_device_limit": False,
            "is_trial": False,
            # subscription-related (nullable)
            "status": None,
            "subscription_type": None,
            "traffic_limit": None,
            "device_limit": None,
            "expire_time": None,
            "reset_time": None,
            "connection_url": None,
        }

        if not menu_data.current_subscription:
            data["trial_available"] = menu_data.is_trial_available and menu_data.available_trial
            return data

        subscription = menu_data.current_subscription

        data.update(
            {
                "has_subscription": True,
                "is_trial": subscription.is_trial,
                "status": subscription.current_status,
                "subscription_type": subscription.limit_type,
                "traffic_limit": i18n_format_traffic_limit(subscription.traffic_limit),
                "device_limit": i18n_format_device_limit(subscription.device_limit),
                "expire_time": i18n_format_expire_time(subscription.expire_at),
                "reset_time": i18n_format_expire_time(
                    get_traffic_reset_delta(subscription.traffic_limit_strategy)
                ),
                "connectable": subscription.is_active,
                "has_device_limit": subscription.has_devices_limit
                if subscription.is_active
                else False,
                "connection_url": config.bot.mini_app_url or subscription.url,
            }
        )

        return data

    except Exception as e:
        raise MenuRenderError(str(e)) from e
