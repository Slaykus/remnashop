from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from src.application.common import Interactor
from src.application.common.dao.ad_link import AdLinkDao
from src.application.common.policy import Permission
from src.application.dto import UserDto
from src.application.dto.ad_link import (
    AdLinkComparisonItemDto,
    AdLinkDailyClickDto,
    AdLinkDto,
    AdLinkStatsDto,
)

_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


class GetAdLinks(Interactor[None, list[AdLinkDto]]):
    required_permission = Permission.VIEW_ADVERTISING

    def __init__(self, ad_link_dao: AdLinkDao) -> None:
        self.ad_link_dao = ad_link_dao

    async def _execute(self, actor: UserDto, data: None) -> list[AdLinkDto]:
        return await self.ad_link_dao.get_all()


class GetAdLinkStats(Interactor[int, AdLinkStatsDto]):
    required_permission = Permission.VIEW_ADVERTISING

    def __init__(self, ad_link_dao: AdLinkDao) -> None:
        self.ad_link_dao = ad_link_dao

    async def _execute(self, actor: UserDto, data: int) -> AdLinkStatsDto:
        return await self.ad_link_dao.get_stats(data)


@dataclass(frozen=True)
class GetAdLinkPeriodStatsInput:
    link_id: int
    days: int  # 0 = all-time


class GetAdLinkPeriodStats(Interactor[GetAdLinkPeriodStatsInput, AdLinkStatsDto]):
    required_permission = Permission.VIEW_ADVERTISING

    def __init__(self, ad_link_dao: AdLinkDao) -> None:
        self.ad_link_dao = ad_link_dao

    async def _execute(
        self, actor: UserDto, data: GetAdLinkPeriodStatsInput
    ) -> AdLinkStatsDto:
        since = (
            _EPOCH
            if data.days == 0
            else datetime.now(timezone.utc) - timedelta(days=data.days)
        )
        return await self.ad_link_dao.get_stats_since(data.link_id, since)


@dataclass(frozen=True)
class GetAdLinkDailyStatsInput:
    link_id: int
    days: int


class GetAdLinkDailyStats(Interactor[GetAdLinkDailyStatsInput, list[AdLinkDailyClickDto]]):
    required_permission = Permission.VIEW_ADVERTISING

    def __init__(self, ad_link_dao: AdLinkDao) -> None:
        self.ad_link_dao = ad_link_dao

    async def _execute(
        self, actor: UserDto, data: GetAdLinkDailyStatsInput
    ) -> list[AdLinkDailyClickDto]:
        since = (
            _EPOCH
            if data.days == 0
            else datetime.now(timezone.utc) - timedelta(days=data.days)
        )
        return await self.ad_link_dao.get_daily_clicks(data.link_id, since)


class GetAllAdLinksComparison(Interactor[None, list[AdLinkComparisonItemDto]]):
    required_permission = Permission.VIEW_ADVERTISING

    def __init__(self, ad_link_dao: AdLinkDao) -> None:
        self.ad_link_dao = ad_link_dao

    async def _execute(
        self, actor: UserDto, data: None
    ) -> list[AdLinkComparisonItemDto]:
        return await self.ad_link_dao.get_all_links_comparison()
