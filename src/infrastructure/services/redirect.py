from typing import Optional

from aiogram import Bot
from aiogram_dialog import BgManagerFactory, ShowMode, StartMode
from loguru import logger

from src.application.common import Redirect
from src.core.constants import TARGET_USER_ID
from src.core.enums import PurchaseType
from src.telegram.states import DashboardUser, MainMenu, Subscription


def _has_telegram_chat(telegram_id: Optional[int]) -> bool:
    """
    Есть ли куда открывать экран.

    У зарегистрированных на сайте телеграмного чата нет, и сайт присылает
    им псевдо-id вида -user.id. Телеграм на такой id отвечает 'chat not
    found', причём не в месте вызова, а внутри фоновой задачи диалога —
    поэтому покупку это не ломало, но трейсбек падал в ленту ошибок на
    каждой оплате с сайта.

    Опознать такого пользователя можно только по знаку id: в 'auth_type'
    у них стоит обычный 'telegram'.
    """
    return telegram_id is not None and telegram_id > 0


class RedirectImpl(Redirect):
    def __init__(
        self,
        bot: Bot,
        bg_manager_factory: BgManagerFactory,
    ) -> None:
        self.bot = bot
        self.bg_manager_factory = bg_manager_factory

    async def to_main_menu(self, telegram_id: int) -> None:
        if not _has_telegram_chat(telegram_id):
            logger.debug(f"Skipping redirect for web-only user '{telegram_id}'")
            return

        bg_manager = self.bg_manager_factory.bg(
            bot=self.bot,
            user_id=telegram_id,
            chat_id=telegram_id,
        )

        await bg_manager.start(
            state=MainMenu.MAIN,
            mode=StartMode.RESET_STACK,
            show_mode=ShowMode.DELETE_AND_SEND,
        )
        logger.info(f"User '{telegram_id}' redirected to main menu")

    async def to_user_editor(self, telegram_id: int, target_user_id: int) -> None:
        if not _has_telegram_chat(telegram_id):
            logger.debug(f"Skipping redirect for web-only user '{telegram_id}'")
            return

        bg_manager = self.bg_manager_factory.bg(
            bot=self.bot,
            user_id=telegram_id,
            chat_id=telegram_id,
        )

        await bg_manager.start(
            state=DashboardUser.MAIN,
            data={TARGET_USER_ID: target_user_id},
            mode=StartMode.RESET_STACK,
            show_mode=ShowMode.DELETE_AND_SEND,
        )
        logger.info(f"User '{telegram_id}' redirected to user editor")

    async def to_success_trial(self, telegram_id: int) -> None:
        if not _has_telegram_chat(telegram_id):
            logger.debug(f"Skipping redirect for web-only user '{telegram_id}'")
            return

        bg_manager = self.bg_manager_factory.bg(
            bot=self.bot,
            user_id=telegram_id,
            chat_id=telegram_id,
        )

        await bg_manager.start(
            state=Subscription.TRIAL,
            mode=StartMode.RESET_STACK,
            show_mode=ShowMode.DELETE_AND_SEND,
        )
        logger.info(f"User '{telegram_id}' redirected to success trial")

    async def to_success_payment(self, telegram_id: int, purchase_type: PurchaseType) -> None:
        if not _has_telegram_chat(telegram_id):
            logger.debug(f"Skipping redirect for web-only user '{telegram_id}'")
            return

        bg_manager = self.bg_manager_factory.bg(
            bot=self.bot,
            user_id=telegram_id,
            chat_id=telegram_id,
        )

        await bg_manager.start(
            state=Subscription.SUCCESS,
            data={"purchase_type": purchase_type},
            mode=StartMode.RESET_STACK,
            show_mode=ShowMode.DELETE_AND_SEND,
        )
        logger.info(f"User '{telegram_id}' redirected to success payment")

    async def to_failed_payment(self, telegram_id: int) -> None:
        if not _has_telegram_chat(telegram_id):
            logger.debug(f"Skipping redirect for web-only user '{telegram_id}'")
            return

        bg_manager = self.bg_manager_factory.bg(
            bot=self.bot,
            user_id=telegram_id,
            chat_id=telegram_id,
        )

        await bg_manager.start(
            state=Subscription.FAILED,
            mode=StartMode.RESET_STACK,
            show_mode=ShowMode.DELETE_AND_SEND,
        )
        logger.info(f"User '{telegram_id}' redirected to failed payment")
