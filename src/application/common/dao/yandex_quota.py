from typing import Optional, Protocol, runtime_checkable

from src.application.dto.yandex_quota import UserYandexQuotaDto


@runtime_checkable
class YandexQuotaDao(Protocol):
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[UserYandexQuotaDto]: ...

    async def upsert(self, dto: UserYandexQuotaDto) -> UserYandexQuotaDto: ...

    async def get_all_restricted(self) -> list[UserYandexQuotaDto]: ...

    async def get_all(self) -> list[UserYandexQuotaDto]: ...
