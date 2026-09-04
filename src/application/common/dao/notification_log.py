from datetime import datetime
from typing import Any, Optional, Protocol, runtime_checkable


@runtime_checkable
class NotificationLogDao(Protocol):
    async def was_sent(self, user_id: int, kind: str) -> bool: ...

    async def sent_user_ids(self, kind: str) -> set[int]:
        """Кому этот повод уже отправляли — одним запросом на всю выборку."""
        ...

    async def mark_sent(
        self,
        user_id: int,
        kind: str,
        details: Optional[dict[str, Any]] = None,
        sent_at: Optional[datetime] = None,
    ) -> bool:
        """
        Записать отправку.

        False — запись уже была, отправлять второй раз нельзя.
        """
        ...
