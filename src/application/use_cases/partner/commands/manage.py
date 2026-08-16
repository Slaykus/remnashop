"""Управление партнёрами: заведение, условия, выплаты."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from loguru import logger

from datetime import datetime, timezone

from src.application.common import Cryptographer, Interactor, Notifier
from src.application.dto import MessagePayloadDto
from src.application.common.dao import AdLinkDao, PartnerDao, UserDao
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
    max_bonus_days: Optional[int] = None


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
                max_bonus_days=data.max_bonus_days,
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


@dataclass(frozen=True)
class ToggleLinkOwnerDto:
    link_id: int
    partner_id: int


class ToggleLinkOwner(Interactor[ToggleLinkOwnerDto, bool]):
    """
    Закрепляет рекламную ссылку за партнёром либо снимает закрепление.

    Возвращает новое состояние: True — ссылка теперь партнёрская.

    Снятие не трогает уже начисленное. Начисления привязаны к платежу и
    партнёру, а не к ссылке: иначе перестановка ссылки задним числом
    переписывала бы историю выплат.
    """

    required_permission = Permission.MANAGE_PARTNERS

    def __init__(
        self,
        uow: UnitOfWork,
        ad_link_dao: AdLinkDao,
        partner_dao: PartnerDao,
    ) -> None:
        self.uow = uow
        self.ad_link_dao = ad_link_dao
        self.partner_dao = partner_dao

    async def _execute(self, actor: UserDto, data: ToggleLinkOwnerDto) -> bool:
        partner = await self.partner_dao.get_by_id(data.partner_id)
        link = await self.ad_link_dao.get_by_id(data.link_id)
        if partner is None or link is None:
            return False

        attach = link.owner_user_id != partner.user_id
        async with self.uow:
            await self.ad_link_dao.set_owner(data.link_id, partner.user_id if attach else None)
            await self.uow.commit()

        logger.info(
            f"[Partner] Link '{link.code}' {'attached to' if attach else 'detached from'} "
            f"partner '{partner.id}' by {actor.log}"
        )
        return attach


@dataclass(frozen=True)
class CreatePartnerLinkDto:
    telegram_id: int
    name: str


class CreatePartnerLink(Interactor[CreatePartnerLinkDto, Optional[str]]):
    """
    Партнёр заводит себе рекламную ссылку сам.

    Прежняя схема делала владельца посредником: партнёр просит ссылку под
    размещение, владелец идёт в бота, создаёт, закрепляет. С пятью
    партнёрами уже неудобно, с двадцатью невозможно.

    Бонусы за переход здесь не задаются: баллы, дни и скидка — деньги
    владельца, и раздавать их партнёр не должен. Владелец проставляется
    сразу, поэтому закреплять вручную ничего не надо.

    Возвращает код созданной ссылки либо None, если человек не партнёр.
    """

    required_permission = Permission.VIEW_OWN_PARTNER_STATS

    def __init__(
        self,
        uow: UnitOfWork,
        ad_link_dao: AdLinkDao,
        partner_dao: PartnerDao,
        user_dao: UserDao,
        cryptographer: Cryptographer,
    ) -> None:
        self.uow = uow
        self.ad_link_dao = ad_link_dao
        self.partner_dao = partner_dao
        self.user_dao = user_dao
        self.cryptographer = cryptographer

    async def _execute(self, actor: UserDto, data: CreatePartnerLinkDto) -> Optional[str]:
        user = await self.user_dao.get_by_telegram_id(data.telegram_id)
        if user is None or user.id is None:
            return None

        partner = await self.partner_dao.get_by_user_id(user.id)
        if partner is None or not partner.is_active:
            return None

        name = data.name.strip()[:64] or "Ссылка"
        code = await self.cryptographer.generate_unique_code(self.ad_link_dao.get_by_code)

        async with self.uow:
            link = await self.ad_link_dao.create(name=name, code=code)
            await self.ad_link_dao.set_owner(link.id, user.id)
            await self.uow.commit()

        logger.info(f"[Partner] Partner '{partner.id}' created link '{code}'")
        return code


@dataclass(frozen=True)
class RequestPayoutDto:
    telegram_id: int


class RequestPayout(Interactor[RequestPayoutDto, Optional[Decimal]]):
    """
    Партнёр просит выплату.

    Возвращает сумму к выплате либо None, если платить нечего, сумма ниже
    порога или запрос уже висит.

    Владельцу уходит уведомление с суммой и реквизитами: без него он должен
    был бы сам обходить всех партнёров и высматривать, у кого накопилось.

    Повторный запрос уведомление не шлёт: партнёр нажмёт трижды, а владелец
    получит три одинаковых сообщения и перестанет их читать.
    """

    required_permission = Permission.VIEW_OWN_PARTNER_STATS

    def __init__(
        self,
        uow: UnitOfWork,
        partner_dao: PartnerDao,
        user_dao: UserDao,
        notifier: Notifier,
    ) -> None:
        self.uow = uow
        self.partner_dao = partner_dao
        self.user_dao = user_dao
        self.notifier = notifier

    async def _execute(self, actor: UserDto, data: RequestPayoutDto) -> Optional[Decimal]:
        user = await self.user_dao.get_by_telegram_id(data.telegram_id)
        if user is None or user.id is None:
            return None

        partner = await self.partner_dao.get_by_user_id(user.id)
        if partner is None or not partner.is_active:
            return None

        if partner.payout_requested_at is not None:
            return None

        # Досчитываем отлежавшее прямо сейчас: иначе партнёр видит сумму,
        # доступную по срокам, а запрос отказывает из-за неотработавшей задачи.
        async with self.uow:
            await self.partner_dao.mark_available()
            await self.uow.commit()

        balance = await self.partner_dao.get_balance(partner.id)
        if balance.available < partner.min_payout:
            return None

        async with self.uow:
            await self.partner_dao.set_payout_requested(partner.id, datetime.now(timezone.utc))
            await self.uow.commit()

        await self.notifier.notify_admins(
            MessagePayloadDto(
                i18n_key="ntf-partner.payout-requested",
                i18n_kwargs={
                    "name": user.name or f"#{user.id}",
                    "amount": str(balance.available),
                    "details": partner.payout_details or "не указаны",
                },
            )
        )
        logger.info(f"[Partner] Partner '{partner.id}' requested payout of {balance.available}")
        return balance.available


@dataclass(frozen=True)
class SavePayoutDetailsDto:
    telegram_id: int
    details: str


class SavePayoutDetails(Interactor[SavePayoutDetailsDto, bool]):
    """
    Партнёр сам вписывает, куда ему платить.

    Свободный текст и никакого разбора на поля: способы у всех разные, а
    структурированная финансовая база — лишняя ответственность там, где
    достаточно строки для перевода.
    """

    required_permission = Permission.VIEW_OWN_PARTNER_STATS

    def __init__(self, uow: UnitOfWork, partner_dao: PartnerDao, user_dao: UserDao) -> None:
        self.uow = uow
        self.partner_dao = partner_dao
        self.user_dao = user_dao

    async def _execute(self, actor: UserDto, data: SavePayoutDetailsDto) -> bool:
        user = await self.user_dao.get_by_telegram_id(data.telegram_id)
        if user is None or user.id is None:
            return False

        partner = await self.partner_dao.get_by_user_id(user.id)
        if partner is None:
            return False

        async with self.uow:
            await self.partner_dao.update_terms(
                partner_id=partner.id, payout_details=data.details.strip()[:512]
            )
            await self.uow.commit()
        return True


@dataclass(frozen=True)
class SetLinkBonusDto:
    telegram_id: int
    code: str
    bonus_days: int


class SetLinkBonus(Interactor[SetLinkBonusDto, Optional[int]]):
    """
    Партнёр назначает бонус своей ссылке.

    Потолок задаёт владелец: бонус раздаётся не деньгами партнёра, и без
    ограничения ему выгодно ставить максимум. Значение выше потолка не
    отклоняем, а подрезаем до него — партнёр видит, что именно применилось,
    и это понятнее отказа без объяснения.

    Возвращает применённое значение либо None, если ссылка не его.
    """

    required_permission = Permission.VIEW_OWN_PARTNER_STATS

    def __init__(
        self,
        uow: UnitOfWork,
        ad_link_dao: AdLinkDao,
        partner_dao: PartnerDao,
        user_dao: UserDao,
    ) -> None:
        self.uow = uow
        self.ad_link_dao = ad_link_dao
        self.partner_dao = partner_dao
        self.user_dao = user_dao

    async def _execute(self, actor: UserDto, data: SetLinkBonusDto) -> Optional[int]:
        user = await self.user_dao.get_by_telegram_id(data.telegram_id)
        if user is None or user.id is None:
            return None

        partner = await self.partner_dao.get_by_user_id(user.id)
        if partner is None:
            return None

        link = await self.ad_link_dao.get_by_code(data.code)
        # Чужую ссылку тронуть нельзя, даже зная её код.
        if link is None or link.owner_user_id != user.id:
            return None

        value = max(0, min(int(data.bonus_days), partner.max_bonus_days))
        link.bonus_days = value
        async with self.uow:
            await self.ad_link_dao.update(link)
            await self.uow.commit()

        logger.info(f"[Partner] Link '{link.code}' bonus set to {value} days")
        return value
