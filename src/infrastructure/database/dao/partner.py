from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from adaptix import Retort
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert

from src.application.common.dao.partner import PartnerDao
from src.application.dto.partner import (
    PartnerBalanceDto,
    PartnerDto,
    PartnerEarningDto,
    PartnerPayoutDto,
)
from src.infrastructure.database.models.ad_link import AdLink, AdLinkUser
from src.infrastructure.database.models.partner import (
    Partner,
    PartnerEarning,
    PartnerPayout,
)
from src.infrastructure.database.models.user import User

from .base import BaseDaoImpl


class PartnerDaoImpl(PartnerDao, BaseDaoImpl):
    # Конструктор объявлен явно, хотя ничего не добавляет к базовому.
    # Без него механика Protocol подменяет __init__ заглушкой, которая
    # вызывается без аргументов, и контейнер зависимостей падает при
    # выдаче DAO — то есть при первом же платеже. У соседних DAO свой
    # конструктор есть, поэтому там это не проявлялось.
    # Поля присваиваются здесь, а не через super(): в цепочке наследования
    # следующим стоит Protocol, и его __init__ аргументы проглатывает. Так
    # же сделано у соседних DAO.
    def __init__(self, session: AsyncSession, retort: Retort) -> None:
        self.session = session
        self.retort = retort

    def _to_dto(self, p: Partner) -> PartnerDto:
        return PartnerDto(
            id=p.id,
            user_id=p.user_id,
            rate_pct=p.rate_pct,
            hold_days=p.hold_days,
            min_payout=p.min_payout,
            is_active=p.is_active,
            payout_details=p.payout_details,
            note=p.note,
            created_at=getattr(p, "created_at", None),
        )

    def _earning_to_dto(self, e: PartnerEarning) -> PartnerEarningDto:
        return PartnerEarningDto(
            id=e.id,
            partner_id=e.partner_id,
            transaction_id=e.transaction_id,
            referred_user_id=e.referred_user_id,
            amount=e.amount,
            rate_pct=e.rate_pct,
            payment_amount=e.payment_amount,
            status=e.status,
            available_at=e.available_at,
            created_at=e.created_at,
            paid_at=e.paid_at,
        )

    async def get_by_id(self, partner_id: int) -> Optional[PartnerDto]:
        p = (
            await self.session.execute(select(Partner).where(Partner.id == partner_id))
        ).scalar_one_or_none()
        return self._to_dto(p) if p else None

    async def get_by_user_id(self, user_id: int) -> Optional[PartnerDto]:
        p = (
            await self.session.execute(select(Partner).where(Partner.user_id == user_id))
        ).scalar_one_or_none()
        return self._to_dto(p) if p else None

    async def get_all(self) -> list[PartnerDto]:
        rows = (await self.session.execute(select(Partner).order_by(Partner.id))).scalars().all()
        return [self._to_dto(p) for p in rows]

    async def create(self, user_id: int) -> PartnerDto:
        # Условия не задаются здесь: значения по умолчанию стоят у колонок,
        # чтобы «договорённость по умолчанию» жила в одном месте.
        p = Partner(user_id=user_id)
        self.session.add(p)
        await self.session.flush()
        return self._to_dto(p)

    async def update_terms(
        self,
        partner_id: int,
        rate_pct: Optional[Decimal] = None,
        hold_days: Optional[int] = None,
        min_payout: Optional[Decimal] = None,
        is_active: Optional[bool] = None,
        payout_details: Optional[str] = None,
    ) -> None:
        values: dict = {}
        if rate_pct is not None:
            values["rate_pct"] = rate_pct
        if hold_days is not None:
            values["hold_days"] = hold_days
        if min_payout is not None:
            values["min_payout"] = min_payout
        if is_active is not None:
            values["is_active"] = is_active
        if payout_details is not None:
            values["payout_details"] = payout_details
        if not values:
            return
        await self.session.execute(
            update(Partner).where(Partner.id == partner_id).values(**values)
        )

    async def _first_touch_partner(self, user_id: int) -> Optional[Partner]:
        """
        Партнёр по правилу первого касания.

        Берём самый ранний переход этого человека по партнёрской ссылке.
        Правило защищает от перехвата: догонять рекламой уже наших клиентов
        партнёру бесполезно, потому что засчитан будет тот, кто привёл
        человека впервые.
        """
        user = (
            await self.session.execute(select(User).where(User.id == user_id))
        ).scalar_one_or_none()
        if user is None or user.telegram_id is None:
            return None

        row = (
            await self.session.execute(
                select(Partner)
                .join(AdLink, AdLink.owner_user_id == Partner.user_id)
                .join(AdLinkUser, AdLinkUser.ad_link_id == AdLink.id)
                .where(AdLinkUser.user_telegram_id == user.telegram_id)
                .order_by(AdLinkUser.created_at.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
        return row

    async def accrue_for_payment(
        self,
        transaction_id: int,
        user_id: int,
        payment_amount: Decimal,
    ) -> Optional[PartnerEarningDto]:
        if payment_amount is None or payment_amount <= 0:
            return None

        partner = await self._first_touch_partner(user_id)
        if partner is None or not partner.is_active:
            return None

        now = datetime.now(timezone.utc)
        rate = Decimal(partner.rate_pct)
        # Округление до копеек вниз: партнёру платим не больше, чем следует
        # по ставке, и сумма не расходится с тем, что видно в отчёте.
        amount = (Decimal(payment_amount) * rate / Decimal(100)).quantize(Decimal("0.01"))
        if amount <= 0:
            return None

        # Один платёж — одно начисление. Вебхук шлюза может прийти повторно,
        # и без этого партнёру начислялось бы дважды за один платёж.
        stmt = (
            insert(PartnerEarning)
            .values(
                partner_id=partner.id,
                transaction_id=transaction_id,
                referred_user_id=user_id,
                amount=amount,
                rate_pct=rate,
                payment_amount=Decimal(payment_amount),
                status="pending",
                available_at=now + timedelta(days=partner.hold_days),
                created_at=now,
            )
            .on_conflict_do_nothing(constraint="uq_partner_earnings_transaction")
            .returning(PartnerEarning)
        )
        created = (await self.session.execute(stmt)).scalar_one_or_none()
        if created is None:
            logger.debug(
                f"[Partner] Earning for transaction '{transaction_id}' already exists, skipping"
            )
            return None

        logger.info(
            f"[Partner] Accrued {amount} ({rate}%) to partner '{partner.id}' "
            f"for transaction '{transaction_id}'"
        )
        return self._earning_to_dto(created)

    async def get_balance(self, partner_id: int) -> PartnerBalanceDto:
        now = datetime.now(timezone.utc)
        row = (
            await self.session.execute(
                select(
                    func.coalesce(
                        func.sum(PartnerEarning.amount).filter(
                            PartnerEarning.status == "pending",
                            PartnerEarning.available_at > now,
                        ),
                        0,
                    ),
                    # Доступно — и отмеченные проходом, и те, у кого срок уже
                    # вышел, но проход ещё не отработал: иначе баланс скакал бы
                    # в зависимости от того, когда в последний раз шла задача.
                    func.coalesce(
                        func.sum(PartnerEarning.amount).filter(
                            PartnerEarning.status.in_(("pending", "available")),
                            PartnerEarning.available_at <= now,
                        ),
                        0,
                    ),
                    func.coalesce(
                        func.sum(PartnerEarning.amount).filter(PartnerEarning.status == "paid"),
                        0,
                    ),
                    func.coalesce(
                        func.sum(PartnerEarning.amount).filter(PartnerEarning.status != "canceled"),
                        0,
                    ),
                    func.count(PartnerEarning.id).filter(PartnerEarning.status != "canceled"),
                ).where(PartnerEarning.partner_id == partner_id)
            )
        ).one()

        return PartnerBalanceDto(
            pending=Decimal(row[0]),
            available=Decimal(row[1]),
            paid=Decimal(row[2]),
            total=Decimal(row[3]),
            payments_count=int(row[4]),
        )

    async def get_earnings(
        self, partner_id: int, limit: int = 50, offset: int = 0
    ) -> list[PartnerEarningDto]:
        rows = (
            (
                await self.session.execute(
                    select(PartnerEarning)
                    .where(PartnerEarning.partner_id == partner_id)
                    .order_by(PartnerEarning.created_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return [self._earning_to_dto(e) for e in rows]

    async def mark_available(self) -> int:
        """
        Переводит отлежавшие начисления в доступные к выплате.

        Статус меняется отдельным проходом, а не вычисляется на лету, чтобы
        «доступно» было фактом в базе: по нему оформляется выплата, и он не
        должен зависеть от того, в какую секунду выполнился запрос.
        """
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            update(PartnerEarning)
            .where(
                PartnerEarning.status == "pending",
                PartnerEarning.available_at <= now,
            )
            .values(status="available")
        )
        count = int(result.rowcount or 0)
        if count:
            logger.info(f"[Partner] {count} earnings became available for payout")
        return count

    async def create_payout(
        self,
        partner_id: int,
        created_by: Optional[int] = None,
        note: Optional[str] = None,
    ) -> Optional[PartnerPayoutDto]:
        partner = (
            await self.session.execute(select(Partner).where(Partner.id == partner_id))
        ).scalar_one_or_none()
        if partner is None:
            return None

        rows = (
            (
                await self.session.execute(
                    select(PartnerEarning).where(
                        PartnerEarning.partner_id == partner_id,
                        PartnerEarning.status == "available",
                    )
                )
            )
            .scalars()
            .all()
        )
        if not rows:
            return None

        total = sum((Decimal(e.amount) for e in rows), Decimal(0))
        # Порог оформления — у партнёра свой. Мелкие выплаты дороже
        # обходятся в переводах, чем стоят сами.
        if total < Decimal(partner.min_payout):
            logger.debug(
                f"[Partner] Payout for '{partner_id}' is {total}, below minimum "
                f"{partner.min_payout} — skipping"
            )
            return None

        now = datetime.now(timezone.utc)
        payout = PartnerPayout(
            partner_id=partner_id,
            amount=total,
            note=note,
            created_at=now,
            created_by=created_by,
        )
        self.session.add(payout)
        await self.session.flush()

        # Начисления закрываются ссылкой на выплату: по ней потом видно,
        # что именно вошло в конкретный перевод.
        await self.session.execute(
            update(PartnerEarning)
            .where(PartnerEarning.id.in_([e.id for e in rows]))
            .values(status="paid", paid_at=now, payout_id=payout.id)
        )

        logger.info(
            f"[Partner] Payout {total} to partner '{partner_id}' covering {len(rows)} earnings"
        )
        return PartnerPayoutDto(
            id=payout.id,
            partner_id=partner_id,
            amount=total,
            note=note,
            created_at=now,
            created_by=created_by,
            earnings_count=len(rows),
        )

    async def get_payouts(self, partner_id: int, limit: int = 20) -> list[PartnerPayoutDto]:
        rows = (
            (
                await self.session.execute(
                    select(PartnerPayout)
                    .where(PartnerPayout.partner_id == partner_id)
                    .order_by(PartnerPayout.created_at.desc())
                    .limit(limit)
                )
            )
            .scalars()
            .all()
        )
        return [
            PartnerPayoutDto(
                id=p.id,
                partner_id=p.partner_id,
                amount=p.amount,
                note=p.note,
                created_at=p.created_at,
                created_by=p.created_by,
            )
            for p in rows
        ]
