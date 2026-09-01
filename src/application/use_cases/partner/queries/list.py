"""Чтение по партнёрам: список для владельца, сводка по одному."""

from dataclasses import dataclass
from typing import Optional

from src.application.common import Interactor
from src.application.common.dao import PartnerDao, UserDao
from src.application.common.policy import Permission
from src.application.dto import (
    PartnerBalanceDto,
    PartnerDto,
    PartnerEarningDto,
    PartnerPayoutDto,
    UserDto,
)


@dataclass(frozen=True)
class PartnerListItemDto:
    """Строка списка партнёров."""

    partner: PartnerDto
    # Имя и тег берём здесь, а не в экране: по одному номеру владельцу
    # приходилось открывать карточки подряд, чтобы понять, кто есть кто.
    name: str
    username: Optional[str]


class GetPartners(Interactor[None, list[PartnerListItemDto]]):
    required_permission = Permission.MANAGE_PARTNERS

    def __init__(self, partner_dao: PartnerDao, user_dao: UserDao) -> None:
        self.partner_dao = partner_dao
        self.user_dao = user_dao

    async def _execute(self, actor: UserDto, data: None) -> list[PartnerListItemDto]:
        partners = await self.partner_dao.get_all()
        items = []
        for partner in partners:
            user = await self.user_dao.get_by_id(partner.user_id)
            items.append(
                PartnerListItemDto(
                    partner=partner,
                    name=(user.name if user else None) or f"#{partner.user_id}",
                    username=user.username if user else None,
                )
            )
        return items


@dataclass(frozen=True)
class PartnerOverviewDto:
    partner: PartnerDto
    balance: PartnerBalanceDto
    earnings: list[PartnerEarningDto]
    payouts: list[PartnerPayoutDto]
    name: str


class GetPartnerOverview(Interactor[int, Optional[PartnerOverviewDto]]):
    """
    Сводка по партнёру: условия, баланс, последние начисления и выплаты.

    Право `MANAGE_PARTNERS` — владельца. Сам партнёр смотрит своё через
    отдельный путь с `VIEW_OWN_PARTNER_STATS`, где идентификатор берётся
    не из запроса, а из того, кто спрашивает.
    """

    required_permission = Permission.MANAGE_PARTNERS

    def __init__(self, partner_dao: PartnerDao, user_dao: UserDao) -> None:
        self.partner_dao = partner_dao
        self.user_dao = user_dao

    async def _execute(self, actor: UserDto, partner_id: int) -> Optional[PartnerOverviewDto]:
        partner = await self.partner_dao.get_by_id(partner_id)
        if partner is None:
            return None

        user = await self.user_dao.get_by_id(partner.user_id)
        return PartnerOverviewDto(
            partner=partner,
            balance=await self.partner_dao.get_balance(partner_id),
            earnings=await self.partner_dao.get_earnings(partner_id, limit=20),
            payouts=await self.partner_dao.get_payouts(partner_id, limit=10),
            name=(user.name if user else None) or f"#{partner.user_id}",
        )


class GetPartnersComparison(Interactor[None, list[dict]]):
    """
    Все партнёры в одной таблице: кто приносит деньги, а кто занимает место.

    Отдельно от карточки: сравнивать по одной карточке нельзя, а именно
    сравнение и отвечает на вопрос, кого поднимать в ставке, а с кем
    расставаться.
    """

    required_permission = Permission.MANAGE_PARTNERS

    def __init__(self, partner_dao: PartnerDao) -> None:
        self.partner_dao = partner_dao

    async def _execute(self, actor: UserDto, data: None) -> list[dict]:
        return await self.partner_dao.get_comparison()
