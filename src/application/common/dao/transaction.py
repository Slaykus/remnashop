from typing import Optional, Protocol, runtime_checkable
from uuid import UUID

from src.application.dto import TransactionDto
from src.core.enums import TransactionStatus


@runtime_checkable
class TransactionDao(Protocol):
    async def create(self, user: TransactionDto) -> TransactionDto: ...

    async def get_by_payment_id(self, payment_id: UUID) -> Optional[TransactionDto]: ...

    async def get_by_user(self, user_telegram_id: int) -> list[TransactionDto]: ...

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[TransactionDto]: ...

    async def get_by_status(self, status: TransactionStatus) -> list[TransactionDto]: ...

    async def update_status(
        self,
        payment_id: UUID,
        status: TransactionStatus,
    ) -> Optional[TransactionDto]: ...

    async def exists(self, payment_id: UUID) -> bool: ...

    async def cancel_old_pending(self, minutes: int = 30) -> int: ...

    async def count(self) -> int: ...
