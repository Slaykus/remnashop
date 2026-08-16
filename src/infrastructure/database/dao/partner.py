from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from adaptix import Retort
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, text, update
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
            max_bonus_days=p.max_bonus_days,
            is_active=p.is_active,
            payout_details=p.payout_details,
            note=p.note,
            created_at=getattr(p, "created_at", None),
            payout_requested_at=p.payout_requested_at,
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
        max_bonus_days: Optional[int] = None,
    ) -> None:
        values: dict = {}
        if max_bonus_days is not None:
            values["max_bonus_days"] = max_bonus_days
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
                # Партнёр не зарабатывает на самом себе: иначе достаточно
                # пройти по своей же ссылке и купить подписку, чтобы вернуть
                # себе долю с каждой собственной оплаты.
                .where(Partner.user_id != user_id)
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

        # Запрос закрыт — иначе отметка висела бы вечно и следующий запрос
        # партнёра не отличался бы от прошлого.
        await self.session.execute(
            update(Partner).where(Partner.id == partner_id).values(payout_requested_at=None)
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

    async def get_daily(self, partner_id: int, owner_user_id: int, days: int = 30) -> list[dict]:
        """
        Дневной ряд по всем ссылкам партнёра: переходы, регистрации, оплаты
        и его заработок.

        Считается одним запросом с полным календарём дат: без него дни без
        событий выпадали бы, и график рисовал бы ровную линию там, где на
        самом деле провал.
        """
        raw = await self.session.execute(
            text(
                """
                WITH days AS (
                    SELECT generate_series(
                        (now() AT TIME ZONE 'UTC')::date - (:days - 1) * INTERVAL '1 day',
                        (now() AT TIME ZONE 'UTC')::date,
                        INTERVAL '1 day'
                    )::date AS day
                ),
                own AS (
                    SELECT id FROM ad_links WHERE owner_user_id = :owner_id
                ),
                clicks AS (
                    SELECT (alu.created_at AT TIME ZONE 'UTC')::date AS day,
                           COUNT(DISTINCT alu.user_telegram_id) AS n
                    FROM ad_link_users alu
                    JOIN own ON own.id = alu.ad_link_id
                    GROUP BY 1
                ),
                earned AS (
                    SELECT (created_at AT TIME ZONE 'UTC')::date AS day,
                           COUNT(*) AS payments,
                           COALESCE(SUM(amount), 0) AS amount
                    FROM partner_earnings
                    WHERE partner_id = :partner_id AND status <> 'canceled'
                    GROUP BY 1
                )
                SELECT d.day,
                       COALESCE(c.n, 0) AS clicks,
                       COALESCE(e.payments, 0) AS payments,
                       COALESCE(e.amount, 0) AS earned
                FROM days d
                LEFT JOIN clicks c ON c.day = d.day
                LEFT JOIN earned e ON e.day = d.day
                ORDER BY d.day
                """
            ).bindparams(days=days, owner_id=owner_user_id, partner_id=partner_id)
        )
        return [
            {
                "day": row["day"].isoformat(),
                "clicks": int(row["clicks"]),
                "payments": int(row["payments"]),
                "earned": float(row["earned"]),
            }
            for row in raw.mappings().all()
        ]

    async def set_payout_requested(self, partner_id: int, when: Optional[datetime]) -> None:
        """Ставит или снимает отметку о запросе выплаты."""
        await self.session.execute(
            update(Partner).where(Partner.id == partner_id).values(payout_requested_at=when)
        )

    async def get_comparison(self) -> list[dict]:
        """
        Все партнёры одной строкой каждый: сколько привели и сколько стоят.

        Одним запросом, а не обходом партнёров по очереди: при десятке
        партнёров обход давал бы десятки запросов на каждое открытие экрана.
        """
        raw = await self.session.execute(
            text(
                """
                SELECT
                    p.id,
                    u.name AS name,
                    u.telegram_id,
                    p.rate_pct,
                    p.is_active,
                    p.payout_requested_at IS NOT NULL AS requested,
                    COALESCE(l.links, 0) AS links,
                    COALESCE(l.clicks, 0) AS clicks,
                    COALESCE(e.payments, 0) AS payments,
                    COALESCE(e.revenue, 0) AS revenue,
                    COALESCE(e.accrued, 0) AS accrued,
                    COALESCE(e.unpaid, 0) AS unpaid
                FROM partners p
                JOIN users u ON u.id = p.user_id
                LEFT JOIN (
                    SELECT owner_user_id,
                           COUNT(*) AS links,
                           COALESCE(SUM(clicks_count), 0) AS clicks
                    FROM ad_links
                    WHERE owner_user_id IS NOT NULL
                    GROUP BY owner_user_id
                ) l ON l.owner_user_id = p.user_id
                LEFT JOIN (
                    SELECT partner_id,
                           COUNT(*) AS payments,
                           COALESCE(SUM(payment_amount), 0) AS revenue,
                           COALESCE(SUM(amount), 0) AS accrued,
                           COALESCE(SUM(amount) FILTER (WHERE status <> 'paid'), 0) AS unpaid
                    FROM partner_earnings
                    WHERE status <> 'canceled'
                    GROUP BY partner_id
                ) e ON e.partner_id = p.id
                ORDER BY COALESCE(e.revenue, 0) DESC, p.id
                """
            )
        )
        return [
            {
                "id": r["id"],
                "name": r["name"] or f"#{r['telegram_id']}",
                "telegram_id": r["telegram_id"],
                "rate_pct": float(r["rate_pct"]),
                "is_active": bool(r["is_active"]),
                "requested": bool(r["requested"]),
                "links": int(r["links"]),
                "clicks": int(r["clicks"]),
                "payments": int(r["payments"]),
                "revenue": float(r["revenue"]),
                "accrued": float(r["accrued"]),
                "unpaid": float(r["unpaid"]),
            }
            for r in raw.mappings().all()
        ]
