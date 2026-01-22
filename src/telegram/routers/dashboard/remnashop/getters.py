from typing import Any

from aiogram_dialog import DialogManager
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from src.application.common.dao import UserDao
from src.application.dto import UserDto
from src.core.config import AppConfig
from src.core.enums import Role


async def remnashop_getter(
    dialog_manager: DialogManager,
    config: AppConfig,
    **kwargs: Any,
) -> dict[str, Any]:
    return {"version": config.build.tag}


@inject
async def admins_getter(
    dialog_manager: DialogManager,
    config: AppConfig,
    user: UserDto,
    user_dao: FromDishka[UserDao],
    **kwargs: Any,
) -> dict[str, Any]:
    admins = await user_dao.filter_by_role(role=[Role.OWNER] + Role.OWNER.get_subordinates())

    admins_dicts = [
        {
            "user_telegram_id": admin.telegram_id,
            "user_name": admin.name,
            "user_role": admin.role,
            "deletable": (
                admin.telegram_id != user.telegram_id
                and admin.role != Role.OWNER
                and admin.role > user.role
            ),
        }
        for admin in admins
    ]

    return {"admins": admins_dicts}
