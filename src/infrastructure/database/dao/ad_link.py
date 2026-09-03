from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional, cast

from adaptix import Retort
from adaptix.conversion import ConversionRetort
from loguru import logger
from sqlalchemy import func, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.common.dao.ad_link import AdLinkDao
from src.application.dto.ad_link import (
    AdLinkComparisonItemDto,
    AdLinkDailyClickDto,
    AdLinkDto,
    AdLinkStatsDto,
    AdLinkUserDto,
)
from src.infrastructure.database.models.ad_link import AdLink, AdLinkUser

from .base import BaseDaoImpl


class AdLinkDaoImpl(AdLinkDao, BaseDaoImpl):
    def __init__(
        self,
        session: AsyncSession,
        retort: Retort,
        conversion_retort: ConversionRetort,
    ) -> None:
        self.session = session
        self.retort = retort
        self.conversion_retort = conversion_retort

        self._convert = self.conversion_retort.get_converter(AdLink, AdLinkDto)
        self._convert_list = self.conversion_retort.get_converter(list[AdLink], list[AdLinkDto])
        self._convert_user = self.conversion_retort.get_converter(AdLinkUser, AdLinkUserDto)

    async def get_all(self) -> list[AdLinkDto]:
        stmt = select(AdLink).order_by(AdLink.created_at.desc())
        result = await self.session.scalars(stmt)
        rows = cast(list, result.all())
        return self._convert_list(rows)

    async def get_by_id(self, id: int) -> Optional[AdLinkDto]:
        stmt = select(AdLink).where(AdLink.id == id)
        row = await self.session.scalar(stmt)
        return self._convert(row) if row else None

    async def get_by_code(self, code: str) -> Optional[AdLinkDto]:
        stmt = select(AdLink).where(AdLink.code == code)
        row = await self.session.scalar(stmt)
        return self._convert(row) if row else None

    async def create(
        self,
        name: str,
        code: str,
        bonus_points: int = 0,
        bonus_days: int = 0,
        bonus_discount_pct: int = 0,
    ) -> AdLinkDto:
        now = datetime.now(timezone.utc)
        row = AdLink(
            code=code,
            name=name,
            is_active=True,
            bonus_points=bonus_points,
            bonus_days=bonus_days,
            bonus_discount_pct=bonus_discount_pct,
            clicks_count=0,
            created_at=now,
            updated_at=now,
        )
        self.session.add(row)
        await self.session.flush()
        await self.session.refresh(row)
        logger.info(f"[AdLink] Created link '{code}' (id={row.id})")
        return self._convert(row)

    async def update(self, dto: AdLinkDto) -> AdLinkDto:
        now = datetime.now(timezone.utc)
        stmt = (
            update(AdLink)
            .where(AdLink.id == dto.id)
            .values(
                name=dto.name,
                code=dto.code,
                is_active=dto.is_active,
                bonus_points=dto.bonus_points,
                bonus_days=dto.bonus_days,
                bonus_discount_pct=dto.bonus_discount_pct,
                promo_text=dto.promo_text,
                promo_photo_id=dto.promo_photo_id,
                promo_media_type=dto.promo_media_type,
                promo_format=dto.promo_format,
                promo_buttons=dto.promo_buttons,
                updated_at=now,
            )
            .returning(AdLink)
        )
        row = await self.session.scalar(stmt)
        logger.debug(f"[AdLink] Updated link id={dto.id}")
        return self._convert(row)  # type: ignore[arg-type]

    async def move_user(self, old_telegram_id: int, new_telegram_id: int) -> None:
        """
        Переносит привязку к рекламным ссылкам на новый telegram_id.

        Нужно при связывании веб-аккаунта с телеграмом: id меняется с
        псевдо-id сайта на настоящий, и без переноса вся история переходов
        остаётся висеть на несуществующем человеке — а партнёр перестаёт
        получать долю с оплат клиента, которого сам же и привёл.

        Сначала убираем те строки, для которых по той же ссылке уже есть
        запись с новым id: переход был засчитан раньше, и уникальный ключ
        не даст перенести поверх.
        """
        await self.session.execute(
            text(
                """
                DELETE FROM ad_link_users AS old
                WHERE old.user_telegram_id = :old_id
                  AND EXISTS (
                      SELECT 1 FROM ad_link_users AS cur
                      WHERE cur.user_telegram_id = :new_id
                        AND cur.ad_link_id = old.ad_link_id
                  )
                """
            ).bindparams(old_id=old_telegram_id, new_id=new_telegram_id)
        )
        result = await self.session.execute(
            update(AdLinkUser)
            .where(AdLinkUser.user_telegram_id == old_telegram_id)
            .values(user_telegram_id=new_telegram_id)
        )
        moved = int(result.rowcount or 0)
        if moved:
            logger.info(
                f"[AdLink] Moved {moved} click(s) from '{old_telegram_id}' to '{new_telegram_id}'"
            )

    async def get_pending_bonus(self, user_telegram_id: int) -> Optional[AdLinkDto]:
        """
        Ссылка, бонус по которой этому человеку ещё не выдан.

        Нужна потому, что бонусные дни нельзя выдать в момент перехода: у
        новичка ещё нет подписки, к которой их добавлять. Выдача
        откладывается до появления подписки, а признаком служит
        bonus_issued = false.
        """
        row = (
            await self.session.execute(
                select(AdLink)
                .join(AdLinkUser, AdLinkUser.ad_link_id == AdLink.id)
                .where(
                    AdLinkUser.user_telegram_id == user_telegram_id,
                    AdLinkUser.bonus_issued.is_(False),
                )
                .order_by(AdLinkUser.created_at.asc())
                .limit(1)
            )
        ).scalar_one_or_none()
        return self._convert(row) if row else None

    async def set_owner(self, link_id: int, owner_user_id: int | None) -> None:
        """
        Закрепляет ссылку за партнёром либо снимает закрепление.

        Отдельным методом, а не полем в общем update: тот вызывается из
        нескольких мест, и владелец там не заполняется — его бы стирало
        при каждой правке названия или бонуса.
        """
        await self.session.execute(
            update(AdLink)
            .where(AdLink.id == link_id)
            .values(owner_user_id=owner_user_id, updated_at=datetime.now(timezone.utc))
        )
        logger.info(f"[AdLink] Link '{link_id}' owner set to '{owner_user_id}'")

    async def delete(self, id: int) -> None:
        stmt = select(AdLink).where(AdLink.id == id)
        row = await self.session.scalar(stmt)
        if row:
            await self.session.delete(row)
            logger.info(f"[AdLink] Deleted link id={id}")

    async def increment_clicks(self, ad_link_id: int) -> None:
        stmt = (
            update(AdLink)
            .where(AdLink.id == ad_link_id)
            .values(clicks_count=AdLink.clicks_count + 1)
        )
        await self.session.execute(stmt)

    async def register_user_click(self, ad_link_id: int, user_telegram_id: int) -> bool:
        now = datetime.now(timezone.utc)
        stmt = (
            insert(AdLinkUser)
            .values(
                ad_link_id=ad_link_id,
                user_telegram_id=user_telegram_id,
                bonus_issued=False,
                created_at=now,
            )
            .on_conflict_do_nothing(constraint="uq_ad_link_users")
        )
        result = await self.session.execute(stmt)
        is_new = result.rowcount == 1
        logger.debug(
            f"[AdLink] Click registered for link_id={ad_link_id}, "
            f"user={user_telegram_id}, new={is_new}"
        )
        return is_new

    async def get_user_click(
        self, ad_link_id: int, user_telegram_id: int
    ) -> Optional[AdLinkUserDto]:
        stmt = select(AdLinkUser).where(
            AdLinkUser.ad_link_id == ad_link_id,
            AdLinkUser.user_telegram_id == user_telegram_id,
        )
        row = await self.session.scalar(stmt)
        return self._convert_user(row) if row else None

    async def mark_bonus_issued(self, ad_link_id: int, user_telegram_id: int) -> None:
        stmt = (
            update(AdLinkUser)
            .where(
                AdLinkUser.ad_link_id == ad_link_id,
                AdLinkUser.user_telegram_id == user_telegram_id,
            )
            .values(bonus_issued=True)
        )
        await self.session.execute(stmt)

    async def get_stats(self, ad_link_id: int) -> AdLinkStatsDto:
        raw = await self.session.execute(
            text(
                """
                SELECT
                    COUNT(DISTINCT alu.user_telegram_id)
                        AS unique_clicks,
                    COUNT(DISTINCT alu.user_telegram_id)
                        FILTER (WHERE alu.bonus_issued = TRUE)
                        AS bonus_issued_count,
                    COUNT(DISTINCT u.id) FILTER (WHERE tr.found) AS trial_count,
                    COUNT(DISTINCT u.id) FILTER (WHERE pay.paid > 0) AS paid_count,
                    COALESCE(SUM(pay.revenue), 0) AS revenue_rub
                FROM ad_link_users alu
                LEFT JOIN users u
                    ON u.telegram_id = alu.user_telegram_id
                -- Подписки и транзакции считаются каждая отдельно. Раньше обе
                -- присоединялись к пользователю сразу, и строки перемножались:
                -- платёж складывался столько раз, сколько у человека записей
                -- подписки. Количества спасал DISTINCT, а сумма врала — по
                -- ссылке fuckaltgirl показывало 135 ₽ вместо 27 ₽.
                LEFT JOIN LATERAL (
                    SELECT TRUE AS found
                    FROM subscriptions s
                    WHERE s.user_id = u.id
                      AND s.is_trial = TRUE
                      AND s.created_at >= alu.created_at
                    LIMIT 1
                ) tr ON TRUE
                LEFT JOIN LATERAL (
                    SELECT
                        COUNT(*) AS paid,
                        COALESCE(SUM((t.pricing->>'final_amount')::NUMERIC), 0) AS revenue
                    FROM transactions t
                    WHERE t.user_id = u.id
                      AND t.status = 'COMPLETED'
                      AND t.created_at >= alu.created_at
                ) pay ON TRUE
                WHERE alu.ad_link_id = :ad_link_id
                """,
            ).bindparams(ad_link_id=ad_link_id)
        )
        row = raw.mappings().one()
        return AdLinkStatsDto(
            unique_clicks=int(row["unique_clicks"] or 0),
            bonus_issued_count=int(row["bonus_issued_count"] or 0),
            trial_count=int(row["trial_count"] or 0),
            paid_count=int(row["paid_count"] or 0),
            revenue_rub=Decimal(str(row["revenue_rub"] or 0)),
        )

    async def get_stats_since(self, ad_link_id: int, since_date: datetime) -> AdLinkStatsDto:
        raw = await self.session.execute(
            text(
                """
                SELECT
                    COUNT(DISTINCT alu.user_telegram_id)
                        AS unique_clicks,
                    COUNT(DISTINCT alu.user_telegram_id)
                        FILTER (WHERE alu.bonus_issued = TRUE)
                        AS bonus_issued_count,
                    COUNT(DISTINCT u.id) FILTER (WHERE tr.found) AS trial_count,
                    COUNT(DISTINCT u.id) FILTER (WHERE pay.paid > 0) AS paid_count,
                    COALESCE(SUM(pay.revenue), 0) AS revenue_rub
                FROM ad_link_users alu
                LEFT JOIN users u
                    ON u.telegram_id = alu.user_telegram_id
                -- Подписки и транзакции считаются каждая отдельно. Раньше обе
                -- присоединялись к пользователю сразу, и строки перемножались:
                -- платёж складывался столько раз, сколько у человека записей
                -- подписки. Количества спасал DISTINCT, а сумма врала — по
                -- ссылке fuckaltgirl показывало 135 ₽ вместо 27 ₽.
                LEFT JOIN LATERAL (
                    SELECT TRUE AS found
                    FROM subscriptions s
                    WHERE s.user_id = u.id
                      AND s.is_trial = TRUE
                      AND s.created_at >= alu.created_at
                    LIMIT 1
                ) tr ON TRUE
                LEFT JOIN LATERAL (
                    SELECT
                        COUNT(*) AS paid,
                        COALESCE(SUM((t.pricing->>'final_amount')::NUMERIC), 0) AS revenue
                    FROM transactions t
                    WHERE t.user_id = u.id
                      AND t.status = 'COMPLETED'
                      AND t.created_at >= alu.created_at
                ) pay ON TRUE
                WHERE alu.ad_link_id = :ad_link_id
                  AND alu.created_at >= :since_date
                """,
            ).bindparams(ad_link_id=ad_link_id, since_date=since_date)
        )
        row = raw.mappings().one()
        return AdLinkStatsDto(
            unique_clicks=int(row["unique_clicks"] or 0),
            bonus_issued_count=int(row["bonus_issued_count"] or 0),
            trial_count=int(row["trial_count"] or 0),
            paid_count=int(row["paid_count"] or 0),
            revenue_rub=Decimal(str(row["revenue_rub"] or 0)),
        )

    async def get_daily_clicks(
        self, ad_link_id: int, since_date: datetime
    ) -> list[AdLinkDailyClickDto]:
        raw = await self.session.execute(
            text(
                """
                SELECT
                    (created_at AT TIME ZONE 'UTC')::date AS day,
                    COUNT(DISTINCT user_telegram_id) AS unique_clicks
                FROM ad_link_users
                WHERE ad_link_id = :ad_link_id
                  AND created_at >= :since_date
                GROUP BY day
                ORDER BY day ASC
                """,
            ).bindparams(ad_link_id=ad_link_id, since_date=since_date)
        )
        return [
            AdLinkDailyClickDto(day=row["day"], unique_clicks=int(row["unique_clicks"]))
            for row in raw.mappings().all()
        ]

    async def get_all_links_comparison(self) -> list[AdLinkComparisonItemDto]:
        raw = await self.session.execute(
            text(
                """
                SELECT
                    al.id,
                    al.name,
                    al.code,
                    al.is_active,
                    al.clicks_count,
                    COUNT(DISTINCT alu.user_telegram_id) AS unique_clicks,
                    COUNT(DISTINCT t.user_id)
                        FILTER (WHERE t.status = 'COMPLETED' AND t.created_at >= alu.created_at)
                        AS paid_count,
                    COALESCE(
                        SUM((t.pricing->>'final_amount')::NUMERIC)
                            FILTER (WHERE t.status = 'COMPLETED' AND t.created_at >= alu.created_at),
                        0
                    ) AS revenue_rub
                FROM ad_links al
                LEFT JOIN ad_link_users alu ON alu.ad_link_id = al.id
                LEFT JOIN users u ON u.telegram_id = alu.user_telegram_id
                LEFT JOIN transactions t ON t.user_id = u.id
                GROUP BY al.id, al.name, al.code, al.is_active, al.clicks_count
                ORDER BY revenue_rub DESC, unique_clicks DESC
                """,
            )
        )
        items = []
        for row in raw.mappings().all():
            unique = int(row["unique_clicks"] or 0)
            paid = int(row["paid_count"] or 0)
            conv = round(paid / unique * 100, 1) if unique > 0 else 0.0
            items.append(
                AdLinkComparisonItemDto(
                    id=int(row["id"]),
                    name=row["name"],
                    code=row["code"],
                    is_active=bool(row["is_active"]),
                    clicks_count=int(row["clicks_count"] or 0),
                    unique_clicks=unique,
                    paid_count=paid,
                    revenue_rub=Decimal(str(row["revenue_rub"] or 0)),
                    conversion_pct=conv,
                )
            )
        return items
