from datetime import datetime, timezone
from typing import Optional, cast

from adaptix import Retort
from adaptix.conversion import ConversionRetort
from loguru import logger
from sqlalchemy import case, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.common.dao.node_quota import NodeQuotaDao
from src.application.dto.node_quota import UserNodeQuotaDto
from src.infrastructure.database.models.node_quota import UserNodeQuota

from .base import BaseDaoImpl


class NodeQuotaDaoImpl(NodeQuotaDao, BaseDaoImpl):
    def __init__(
        self,
        session: AsyncSession,
        retort: Retort,
        conversion_retort: ConversionRetort,
    ) -> None:
        self.session = session
        self.retort = retort
        self.conversion_retort = conversion_retort

        self._convert = self.conversion_retort.get_converter(UserNodeQuota, UserNodeQuotaDto)
        self._convert_list = self.conversion_retort.get_converter(
            list[UserNodeQuota], list[UserNodeQuotaDto]
        )

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[UserNodeQuotaDto]:
        stmt = select(UserNodeQuota).where(UserNodeQuota.user_telegram_id == telegram_id)
        row = await self.session.scalar(stmt)
        if row:
            logger.debug(f"[NodeQuota] Found quota record for telegram_id={telegram_id}")
            return self._convert(row)
        logger.debug(f"[NodeQuota] No quota record for telegram_id={telegram_id}")
        return None

    async def upsert(self, dto: UserNodeQuotaDto) -> UserNodeQuotaDto:
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
            insert(UserNodeQuota)
            .values(**values, created_at=now)
            .on_conflict_do_update(
                index_elements=["user_telegram_id"],
                set_={k: v for k, v in values.items() if k != "user_telegram_id"},
            )
            .returning(UserNodeQuota)
        )
        row = await self.session.scalar(stmt)
        logger.debug(f"[NodeQuota] Upserted quota for telegram_id={dto.user_telegram_id}")
        return self._convert(row)  # type: ignore[arg-type]

    async def get_all_restricted(self) -> list[UserNodeQuotaDto]:
        stmt = (
            select(UserNodeQuota)
            .where(UserNodeQuota.is_restricted.is_(True))
            .order_by(UserNodeQuota.user_telegram_id.asc())
        )
        result = await self.session.scalars(stmt)
        rows = cast(list, result.all())
        logger.debug(f"[NodeQuota] Found {len(rows)} restricted users")
        return self._convert_list(rows)

    async def get_all(self) -> list[UserNodeQuotaDto]:
        stmt = select(UserNodeQuota).order_by(UserNodeQuota.user_telegram_id.asc())
        result = await self.session.scalars(stmt)
        rows = cast(list, result.all())
        return self._convert_list(rows)

    async def reset_monthly(
        self,
        period_start: datetime,
        keep_restricted_ids: list[int] | None = None,
    ) -> int:
        now = datetime.now(timezone.utc)
        keep_restricted_ids = keep_restricted_ids or []

        values = {
            "period_start": period_start,
            "used_bytes": 0,
            "reset_baseline_bytes": 0,
            "warned_at": None,
            "updated_at": now,
        }

        if keep_restricted_ids:
            values["is_restricted"] = case(
                (UserNodeQuota.user_telegram_id.in_(keep_restricted_ids), True),
                else_=False,
            )
            values["restricted_at"] = case(
                (
                    UserNodeQuota.user_telegram_id.in_(keep_restricted_ids),
                    UserNodeQuota.restricted_at,
                ),
                else_=None,
            )
        else:
            values["is_restricted"] = False
            values["restricted_at"] = None

        result = await self.session.execute(update(UserNodeQuota).values(**values))
        count = cast(int, result.rowcount or 0)  # type: ignore[attr-defined]
        logger.info(
            f"[NodeQuota] Monthly reset applied to '{count}' quota records; "
            f"kept restricted: '{len(keep_restricted_ids)}'"
        )
        return count
