from decimal import Decimal
from typing import Optional, Protocol, runtime_checkable

from src.application.dto.partner import (
    PartnerBalanceDto,
    PartnerDto,
    PartnerEarningDto,
    PartnerPayoutDto,
)


@runtime_checkable
class PartnerDao(Protocol):
    async def get_by_id(self, partner_id: int) -> Optional[PartnerDto]: ...

    async def get_by_user_id(self, user_id: int) -> Optional[PartnerDto]: ...

    async def get_all(self) -> list[PartnerDto]: ...

    async def create(self, user_id: int) -> PartnerDto: ...

    async def update_terms(
        self,
        partner_id: int,
        rate_pct: Optional[Decimal] = None,
        hold_days: Optional[int] = None,
        min_payout: Optional[Decimal] = None,
        is_active: Optional[bool] = None,
        payout_details: Optional[str] = None,
        max_bonus_days: Optional[int] = None,
    ) -> None: ...

    async def accrue_for_payment(
        self,
        transaction_id: int,
        user_id: int,
        payment_amount: Decimal,
    ) -> Optional[PartnerEarningDto]:
        """
        Начисляет партнёру долю с подтверждённого платежа.

        None — начислять некому либо начисление уже есть.
        """
        ...

    async def get_balance(self, partner_id: int) -> PartnerBalanceDto: ...

    async def get_earnings(
        self, partner_id: int, limit: int = 50, offset: int = 0
    ) -> list[PartnerEarningDto]: ...

    async def mark_available(self) -> int:
        """Переводит начисления с вышедшим сроком удержания в доступные."""
        ...

    async def create_payout(
        self, partner_id: int, created_by: Optional[int] = None, note: Optional[str] = None
    ) -> Optional[PartnerPayoutDto]:
        """
        Оформляет выплату всем доступным начислениям партнёра.

        None — платить нечего либо сумма ниже минимальной.
        """
        ...

    async def get_payouts(self, partner_id: int, limit: int = 20) -> list[PartnerPayoutDto]: ...

    async def set_payout_requested(self, partner_id: int, when: object) -> None: ...

    async def get_comparison(self) -> list[dict]: ...

    async def get_daily(
        self, partner_id: int, owner_user_id: int, days: int = 30
    ) -> list[dict]: ...
