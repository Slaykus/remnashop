from datetime import datetime
from typing import Optional, Protocol, runtime_checkable

from src.application.dto.node_quota import UserNodeQuotaDto


@runtime_checkable
class NodeQuotaDao(Protocol):
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[UserNodeQuotaDto]: ...

    async def upsert(self, dto: UserNodeQuotaDto) -> UserNodeQuotaDto: ...

    async def get_all_restricted(self) -> list[UserNodeQuotaDto]: ...

    async def get_all(self) -> list[UserNodeQuotaDto]: ...

    async def reset_monthly(
        self,
        period_start: datetime,
        keep_restricted_ids: list[int] | None = None,
    ) -> int: ...
