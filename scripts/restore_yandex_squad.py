import asyncio

from dishka import Scope

from src.application.common import Remnawave
from src.application.common.dao import SubscriptionDao
from src.core.config import AppConfig
from src.core.logger import setup_logger
from src.infrastructure.di import create_taskiq_container
from src.infrastructure.taskiq.tasks.yandex_traffic import _restore_yandex_squad_for_active_users
from src.telegram.dispatcher import get_bg_manager_factory, get_dispatcher, setup_dispatcher


async def main() -> None:
    config = AppConfig.get()
    setup_logger(config)

    dispatcher = get_dispatcher(config)
    bg_manager_factory = get_bg_manager_factory(dispatcher)
    setup_dispatcher(dispatcher)

    container = create_taskiq_container(config, bg_manager_factory)
    try:
        async with container(scope=Scope.REQUEST) as request_container:
            remnawave = await request_container.get(Remnawave)
            subscription_dao = await request_container.get(SubscriptionDao)
            await _restore_yandex_squad_for_active_users(
                config=config,
                remnawave=remnawave,
                subscription_dao=subscription_dao,
            )
    finally:
        await container.close()


if __name__ == "__main__":
    asyncio.run(main())
