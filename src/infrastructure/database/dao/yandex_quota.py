from typing import Optional, cast
from datetime import datetime, timezone

from adaptix import Retort
from adaptix.conversion import ConversionRetort
from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.common.dao.yandex_quota import YandexQuotaDao
from src.application.dto.yandex_quota import UserYandexQuotaDto
from src.infrastructure.database.models.yandex_quota import UserYandexQuota

from .base import BaseDaoImpl


class YandexQuotaDaoImpl(YandexQuotaDao, BaseDaoImpl):
    def __init__(
        self,
        session: AsyncSession,
        retort: Retort,
        conversion_retort: ConversionRetort,
    ) -> None:
        self.session = session
        self.retort = retort
        self.conversion_retort = conversion_retort

        self._convert = self.conversion_retort.get_converter(UserYandexQuota, UserYandexQuotaDto)
        self._convert_list = self.conversion_retort.get_converter(
            list[UserYandexQuota], list[UserYandexQuotaDto]
        )

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[UserYandexQuotaDto]:
        stmt = select(UserYandexQuota).where(UserYandexQuota.user_telegram_id == telegram_id)
        row = await self.session.scalar(stmt)
        if row:
            logger.debug(f"[YandexQuota] Found quota record for telegram_id={telegram_id}")
            return self._convert(row)
        logger.debug(f"[YandexQuota] No quota record for telegram_id={telegram_id}")
        return None

    async def upsert(self, dto: UserYandexQuotaDto) -> UserYandexQuotaDto:
        now = datetime.now(timezone.utc)
        values = {
            "user_telegram_id": dto.user_telegram_id,
            "is_restricted": dto.is_restricted,
            "period_start": dto.period_start,
            "used_bytes": dto.used_bytes,
            "reset_baseline_bytes": dto.reset_baseline_bytes,
            "last_checked_at": dto.last_checked_at,
            "warned_at": dto.warned_at,
            "restricted_at": dto.restricted_at,
            "updated_at": now,
        }

        stmt = (
            insert(UserYandexQuota)
            .values(**values, created_at=now)
            .on_conflict_do_update(
                index_elements=["user_telegram_id"],
                set_={k: v for k, v in values.items() if k != "user_telegram_id"},
            )
            .returning(UserYandexQuota)
        )
        row = await self.session.scalar(stmt)
        logger.debug(f"[YandexQuota] Upserted quota for telegram_id={dto.user_telegram_id}")
        return self._convert(row)  # type: ignore[arg-type]

    async def get_all_restricted(self) -> list[UserYandexQuotaDto]:
        stmt = select(UserYandexQuota).where(UserYandexQuota.is_restricted.is_(True))
        result = await self.session.scalars(stmt)
        rows = cast(list, result.all())
        logger.debug(f"[YandexQuota] Found {len(rows)} restricted users")
        return self._convert_list(rows)

    async def get_all(self) -> list[UserYandexQuotaDto]:
        stmt = select(UserYandexQuota)
        result = await self.session.scalars(stmt)
        rows = cast(list, result.all())
        return self._convert_list(rows)
