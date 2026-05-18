from typing import Final

from src.application.common import Interactor

from .commands.crud import CreateAdLink, DeleteAdLink, UpdateAdLink
from .commands.process_click import ProcessAdClick
from .queries.list import (
    GetAdLinkDailyStats,
    GetAdLinkPeriodStats,
    GetAdLinkStats,
    GetAdLinks,
    GetAllAdLinksComparison,
)

AD_LINK_USE_CASES: Final[tuple[type[Interactor], ...]] = (
    ProcessAdClick,
    CreateAdLink,
    UpdateAdLink,
    DeleteAdLink,
    GetAdLinks,
    GetAdLinkStats,
    GetAdLinkPeriodStats,
    GetAdLinkDailyStats,
    GetAllAdLinksComparison,
)
