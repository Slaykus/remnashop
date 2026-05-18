from datetime import datetime
from typing import Optional, Protocol, runtime_checkable

from src.application.dto.ad_link import (
    AdLinkComparisonItemDto,
    AdLinkDailyClickDto,
    AdLinkDto,
    AdLinkStatsDto,
    AdLinkUserDto,
)


@runtime_checkable
class AdLinkDao(Protocol):
    async def get_all(self) -> list[AdLinkDto]: ...

    async def get_by_id(self, id: int) -> Optional[AdLinkDto]: ...

    async def get_by_code(self, code: str) -> Optional[AdLinkDto]: ...

    async def create(
        self,
        name: str,
        code: str,
        bonus_points: int = 0,
        bonus_days: int = 0,
        bonus_discount_pct: int = 0,
    ) -> AdLinkDto: ...

    async def update(self, dto: AdLinkDto) -> AdLinkDto: ...

    async def delete(self, id: int) -> None: ...

    async def increment_clicks(self, ad_link_id: int) -> None: ...

    async def register_user_click(self, ad_link_id: int, user_telegram_id: int) -> bool: ...

    async def get_user_click(
        self, ad_link_id: int, user_telegram_id: int
    ) -> Optional[AdLinkUserDto]: ...

    async def mark_bonus_issued(self, ad_link_id: int, user_telegram_id: int) -> None: ...

    async def get_stats(self, ad_link_id: int) -> AdLinkStatsDto: ...

    async def get_stats_since(
        self, ad_link_id: int, since_date: datetime
    ) -> AdLinkStatsDto: ...

    async def get_daily_clicks(
        self, ad_link_id: int, since_date: datetime
    ) -> list[AdLinkDailyClickDto]: ...

    async def get_all_links_comparison(self) -> list[AdLinkComparisonItemDto]: ...
