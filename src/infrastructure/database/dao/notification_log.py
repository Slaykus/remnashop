from datetime import datetime, timezone
from typing import Any, Optional

from loguru import logger
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.common.dao.notification_log import NotificationLogDao
from src.infrastructure.database.models import UserNotificationLog

from .base import BaseDaoImpl


class NotificationLogDaoImpl(NotificationLogDao, BaseDaoImpl):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def was_sent(self, user_id: int, kind: str) -> bool:
        stmt = select(UserNotificationLog.id).where(
            UserNotificationLog.user_id == user_id,
            UserNotificationLog.kind == kind,
        )
        return await self.session.scalar(stmt) is not None

    async def sent_user_ids(self, kind: str) -> set[int]:
        stmt = select(UserNotificationLog.user_id).where(UserNotificationLog.kind == kind)
        rows = await self.session.scalars(stmt)
        return set(rows.all())

    async def mark_sent(
        self,
        user_id: int,
        kind: str,
        details: Optional[dict[str, Any]] = None,
        sent_at: Optional[datetime] = None,
    ) -> bool:
        # Вставка с игнорированием конфликта, а не «проверить и записать»:
        # между проверкой и записью задача может успеть отработать второй
        # раз, и человек получит два письма.
        stmt = (
            insert(UserNotificationLog)
            .values(
                user_id=user_id,
                kind=kind,
                details=details,
                sent_at=sent_at or datetime.now(timezone.utc),
            )
            .on_conflict_do_nothing(constraint="uq_user_notification_log")
            .returning(UserNotificationLog.id)
        )
        created = await self.session.scalar(stmt)
        if created is None:
            logger.debug(f"[Reactivation] '{kind}' already sent to user '{user_id}', skipping")
            return False
        return True
