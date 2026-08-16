"""Управление партнёрами: заведение, условия, выплаты."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from loguru import logger

from src.application.common import Interactor
from src.application.common.dao import PartnerDao, UserDao
from src.application.common.policy import Permission
from src.application.common.uow import UnitOfWork
from src.application.dto import PartnerDto, PartnerPayoutDto, UserDto
from src.core.enums import Role


@dataclass(frozen=True)
class CreatePartnerDto:
    telegram_id: int


class CreatePartner(Interactor[CreatePartnerDto, Optional[PartnerDto]]):
    required_permission = Permission.MANAGE_PARTNERS

    def __init__(self, uow: UnitOfWork, partner_dao: PartnerDao, user_dao: UserDao) -> None:
        self.uow = uow
        self.partner_dao = partner_dao
        self.user_dao = user_dao

    async def _execute(self, actor: UserDto, data: CreatePartnerDto) -> Optional[PartnerDto]:
        user = await self.user_dao.get_by_telegram_id(data.telegram_id)
        if user is None or user.id is None:
            logger.warning(f"[Partner] User '{data.telegram_id}' not found, cannot make partner")
            return None

        existing = await self.partner_dao.get_by_user_id(user.id)
        if existing is not None:
            return existing

        async with self.uow:
            partner = await self.partner_dao.create(user.id)
            # Роль меняем здесь же: без неё человек не увидит свой раздел,
            # а партнёрство без доступа к собственным цифрам бессмысленно.
            # Владельца и разработчиков не трогаем — понижать их права,
            # чтобы выдать партнёрство, было бы хуже некуда.
            if user.role not in (Role.OWNER, Role.DEV, Role.ADMIN):
                user.role = Role.PARTNER
                await self.user_dao.update(user)
            await self.uow.commit()

        logger.info(f"[Partner] Created partner '{partner.id}' for user {user.log}")
        return partner


@dataclass(frozen=True)
class UpdatePartnerTermsDto:
    partner_id: int
    rate_pct: Optional[Decimal] = None
    hold_days: Optional[int] = None
    min_payout: Optional[Decimal] = None
    is_active: Optional[bool] = None
    payout_details: Optional[str] = None


class UpdatePartnerTerms(Interactor[UpdatePartnerTermsDto, None]):
    required_permission = Permission.MANAGE_PARTNERS

    def __init__(self, uow: UnitOfWork, partner_dao: PartnerDao) -> None:
        self.uow = uow
        self.partner_dao = partner_dao

    async def _execute(self, actor: UserDto, data: UpdatePartnerTermsDto) -> None:
        async with self.uow:
            await self.partner_dao.update_terms(
                partner_id=data.partner_id,
                rate_pct=data.rate_pct,
                hold_days=data.hold_days,
                min_payout=data.min_payout,
                is_active=data.is_active,
                payout_details=data.payout_details,
            )
            await self.uow.commit()

        # Новые условия действуют только вперёд: прошлые начисления хранят
        # свою ставку и пересчёту не подлежат.
        logger.info(f"[Partner] Terms updated for partner '{data.partner_id}' by {actor.log}")


@dataclass(frozen=True)
class PayPartnerDto:
    partner_id: int
    note: Optional[str] = None


class PayPartner(Interactor[PayPartnerDto, Optional[PartnerPayoutDto]]):
    required_permission = Permission.MANAGE_PARTNERS

    def __init__(self, uow: UnitOfWork, partner_dao: PartnerDao) -> None:
        self.uow = uow
        self.partner_dao = partner_dao

    async def _execute(self, actor: UserDto, data: PayPartnerDto) -> Optional[PartnerPayoutDto]:
        async with self.uow:
            # Сначала добираем отлежавшее: иначе выплата пропустила бы
            # начисления, у которых срок вышел минуту назад.
            await self.partner_dao.mark_available()
            payout = await self.partner_dao.create_payout(
                partner_id=data.partner_id,
                created_by=actor.id,
                note=data.note,
            )
            await self.uow.commit()

        if payout is None:
            logger.info(f"[Partner] Nothing to pay for partner '{data.partner_id}'")
        return payout


class MarkPartnerEarningsAvailable(Interactor[None, int]):
    """Регулярный проход: отлежавшие начисления становятся доступными."""

    required_permission = None

    def __init__(self, uow: UnitOfWork, partner_dao: PartnerDao) -> None:
        self.uow = uow
        self.partner_dao = partner_dao

    async def _execute(self, actor: UserDto, data: None) -> int:
        async with self.uow:
            count = await self.partner_dao.mark_available()
            await self.uow.commit()
        return count
