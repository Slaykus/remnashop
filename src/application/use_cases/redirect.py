from dataclasses import dataclass
from typing import Optional

from loguru import logger

from src.application.common import Interactor, Notifier, Redirect
from src.application.common.dao import UserDao
from src.application.common.policy import Permission
from src.application.dto import UserDto


@dataclass(frozen=True)
class RedirectMenuDto:
    telegram_id: int


class RedirectMenu(Interactor[RedirectMenuDto, None]):
    required_permission: Optional[Permission] = None

    def __init__(
        self,
        user_dao: UserDao,
        redirect: Redirect,
        notifier: Notifier,
    ) -> None:
        self.user_dao = user_dao
        self.redirect = redirect
        self.notifier = notifier

    async def _execute(self, actor: UserDto, data: RedirectMenuDto) -> None:
        user = await self.user_dao.get_by_telegram_id(data.telegram_id)

        if user is None:
            logger.warning(f"User with telegram_id '{data.telegram_id}' not found for redirection")
            return

        if user.is_privileged:
            await self.notifier.notify_user(user, i18n_key="ntf-error.lost-context")
            logger.debug(f"Skipping redirection for privileged user '{data.telegram_id}'")
            return

        await self.notifier.notify_user(user, i18n_key="ntf-error.lost-context-restart")
        await self.redirect.to_main_menu(data.telegram_id)
