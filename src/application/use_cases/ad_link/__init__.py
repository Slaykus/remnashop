from typing import Final

from src.application.common import Interactor

from .commands.crud import CreateAdLink, DeleteAdLink, UpdateAdLink
from .commands.process_click import ApplyPendingAdBonus, ProcessAdClick
from .queries.list import (
    GetAdLinkDailyStats,
    GetAdLinkPeriodStats,
    GetAdLinkStats,
    GetAdLinks,
    GetAllAdLinksComparison,
)
from .queries.validate import ValidateAdLinkCode

AD_LINK_USE_CASES: Final[tuple[type[Interactor], ...]] = (
    ProcessAdClick,
    ApplyPendingAdBonus,
    CreateAdLink,
    UpdateAdLink,
    DeleteAdLink,
    GetAdLinks,
    GetAdLinkStats,
    GetAdLinkPeriodStats,
    GetAdLinkDailyStats,
    GetAllAdLinksComparison,
    # Проверка кода при входе в бота по deep link. Класс существовал и
    # вызывался из AccessMiddleware, но в этот список не попадал — и любой
    # переход вида ?start=ad_КОД падал в NoFactoryError. Не всплывало,
    # пока все рекламные ссылки вели на посадочную сайта.
    ValidateAdLinkCode,
)
