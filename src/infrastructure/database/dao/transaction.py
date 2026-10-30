from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Iterable, Optional, cast
from uuid import UUID

from adaptix import Retort
from adaptix.conversion import ConversionRetort
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy import Numeric, and_, case, false, func, or_, select, text, update
from sqlalchemy import cast as sql_cast
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.common.dao import TransactionDao
from src.application.dto import GatewayStatsDto, PlanIncomeDto, TransactionDto, UserPaymentStatsDto
from src.application.dto.admin_payments import (
    AdminPaymentRow,
    AdminPaymentsPage,
    AdminPaymentsQuery,
)
from src.core.enums import Currency, PaymentGatewayType, TransactionStatus
from src.core.utils.time import datetime_now
from src.infrastructure.database.models import Transaction, User


class TransactionDaoImpl(TransactionDao):
    def __init__(
        self,
        session: AsyncSession,
        retort: Retort,
        conversion_retort: ConversionRetort,
        redis: Redis,
    ) -> None:
        self.session = session
        self.retort = retort
        self.conversion_retort = conversion_retort
        self.redis = redis

        self._convert_to_dto = self.conversion_retort.get_converter(Transaction, TransactionDto)
        self._convert_to_dto_list = self.conversion_retort.get_converter(
            list[Transaction],
            list[TransactionDto],
        )

    async def create(self, transaction: TransactionDto) -> TransactionDto:
        transaction_data = self.retort.dump(transaction)
        transaction_data.pop("id", None)
        db_transaction = Transaction(**transaction_data)

        self.session.add(db_transaction)
        await self.session.flush()

        logger.debug(f"Created new transaction '{transaction.payment_id}'")
        return self._convert_to_dto(db_transaction)

    async def update(self, transaction: TransactionDto) -> Optional[TransactionDto]:
        if not transaction.changed_data:
            logger.warning("No changes detected in transaction, skipping update")
            return None

        stmt = (
            update(Transaction)
            .where(Transaction.payment_id == transaction.payment_id)
            .values(**transaction.changed_data)
            .returning(Transaction)
        )
        db_transaction = await self.session.scalar(stmt)

        if db_transaction:
            logger.debug(
                f"Transaction '{transaction.payment_id}' updated with '{transaction.changed_data}'"
            )
            return self._convert_to_dto(db_transaction)

        logger.warning(f"Failed to update transaction '{transaction.payment_id}': not found")
        return None

    async def get_by_payment_id(self, payment_id: UUID) -> Optional[TransactionDto]:
        stmt = select(Transaction).where(Transaction.payment_id == payment_id)
        db_transaction = await self.session.scalar(stmt)

        if db_transaction:
            logger.debug(f"Transaction '{payment_id}' found")
            return self._convert_to_dto(db_transaction)

        logger.debug(f"Transaction '{payment_id}' not found")
        return None

    async def get_by_user(self, user_id: int) -> list[TransactionDto]:
        stmt = (
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.created_at.desc())
        )
        result = await self.session.scalars(stmt)
        db_transactions = cast(list, result.all())

        logger.debug(f"Retrieved '{len(db_transactions)}' transactions for user_id '{user_id}'")
        return self._convert_to_dto_list(db_transactions)

    async def list_since(
        self,
        since: Optional[datetime] = None,
        after_id: int = 0,
        limit: int = 500,
    ) -> list[TransactionDto]:
        """
        Пачка transactions для внешнего инкрементального сбора.

        Курсор по возрастающему id, а не offset: между страницами
        дописываются новые строки, и offset начал бы их пропускать молча.
        Сортировка тоже по id — у строк, созданных одной транзакцией,
        даты совпадают, и порядок между ними не определён.

        Границу берём включительно: спрашивающий передаёт последнюю
        виденную дату, и повторно приехавшая строка ему не мешает, а вот
        потерянная — мешает.
        """
        stmt = select(Transaction).where(Transaction.id > after_id)

        if since is not None:
            stmt = stmt.where(Transaction.created_at >= since)

        stmt = stmt.order_by(Transaction.id).limit(limit)

        result = await self.session.scalars(stmt)
        rows = cast(list, result.all())

        logger.debug(
            f"Retrieved '{len(rows)}' transactions changed since '{since}' "
            f"after id '{after_id}' with limit '{limit}'"
        )
        return self._convert_to_dto_list(rows)

    async def get_all(self, limit: int = 100, offset: int = 0) -> list[TransactionDto]:
        stmt = (
            select(Transaction).limit(limit).offset(offset).order_by(Transaction.created_at.desc())
        )
        result = await self.session.scalars(stmt)
        db_transactions = cast(list, result.all())

        logger.debug(
            f"Retrieved '{len(db_transactions)}' transactions "
            f"with limit '{limit}' and offset '{offset}'"
        )
        return self._convert_to_dto_list(db_transactions)

    async def get_by_status(self, status: TransactionStatus) -> list[TransactionDto]:
        stmt = select(Transaction).where(Transaction.status == status)
        result = await self.session.scalars(stmt)
        db_transactions = cast(list, result.all())

        logger.debug(f"Found '{len(db_transactions)}' transactions with status '{status}'")
        return self._convert_to_dto_list(db_transactions)

    async def get_failed_purchases_since(self, since: datetime) -> list[TransactionDto]:
        """
        Оплаченные покупки, у которых не прошла выдача, не старше since.

        Без тестовых — их деньги возвращаются сразу. Без подарков — у них
        своя выдача кодом, и её сбой здесь не отмечается.
        """
        stmt = (
            select(Transaction)
            .where(
                Transaction.status == TransactionStatus.FAILED,
                Transaction.is_test.is_(False),
                Transaction.is_gift.is_(False),
                Transaction.created_at >= since,
            )
            .order_by(Transaction.created_at)
        )
        result = await self.session.scalars(stmt)
        return self._convert_to_dto_list(cast(list, result.all()))

    async def update_status(
        self,
        payment_id: UUID,
        status: TransactionStatus,
    ) -> Optional[TransactionDto]:
        stmt = (
            update(Transaction)
            .where(Transaction.payment_id == payment_id)
            .values(status=status)
            .returning(Transaction)
        )
        db_transaction = await self.session.scalar(stmt)

        if db_transaction:
            logger.debug(f"Transaction '{payment_id}' status updated to '{status}'")
            return self._convert_to_dto(db_transaction)

        logger.warning(f"Failed to update transaction '{payment_id}': not found")
        return None

    async def transition_status(
        self,
        payment_id: UUID,
        new_status: TransactionStatus,
        allowed_current: Iterable[TransactionStatus],
    ) -> Optional[TransactionDto]:
        stmt = (
            update(Transaction)
            .where(
                Transaction.payment_id == payment_id,
                Transaction.status.in_(tuple(allowed_current)),
            )
            .values(status=new_status)
            .returning(Transaction)
        )
        db_transaction = await self.session.scalar(stmt)
        if db_transaction:
            logger.debug(f"Transaction '{payment_id}' transitioned to '{new_status}'")
            return self._convert_to_dto(db_transaction)
        logger.info(f"Transaction '{payment_id}' transition to '{new_status}' did not match")
        return None

    async def exists(self, payment_id: UUID) -> bool:
        stmt = select(select(Transaction).where(Transaction.payment_id == payment_id).exists())
        is_exists = await self.session.scalar(stmt) or False

        logger.debug(f"Transaction '{payment_id}' existence status is '{is_exists}'")
        return is_exists

    async def cancel_old(self, minutes: int) -> int:
        threshold = datetime_now() - timedelta(minutes=minutes)

        stmt = (
            update(Transaction)
            .where(Transaction.status == TransactionStatus.PENDING)
            .where(Transaction.created_at < threshold)
            .values(status=TransactionStatus.CANCELED)
        )
        result = await self.session.execute(stmt)
        count = result.rowcount  # type: ignore[attr-defined]

        if count > 0:
            logger.debug(f"Cancelled '{count}' pending transactions older than '{minutes}' minutes")
        else:
            logger.debug(f"No pending transactions older than '{minutes}' minutes found to cancel")

        return cast(int, count)

    async def count(self) -> int:
        stmt = select(func.count()).select_from(Transaction)
        total = await self.session.scalar(stmt) or 0

        logger.debug(f"Total transactions count is '{total}'")
        return total

    async def count_paying_users(self) -> int:
        stmt = select(func.count(func.distinct(Transaction.user_id))).where(
            Transaction.status == TransactionStatus.COMPLETED
        )

        return await self.session.scalar(stmt) or 0

    async def count_total(self) -> int:
        stmt = select(func.count()).select_from(Transaction)
        return await self.session.scalar(stmt) or 0

    async def count_completed(self) -> int:
        stmt = (
            select(func.count())
            .select_from(Transaction)
            .where(Transaction.status == TransactionStatus.COMPLETED)
        )
        return await self.session.scalar(stmt) or 0

    async def count_free(self) -> int:
        stmt = (
            select(func.count())
            .select_from(Transaction)
            .where(Transaction.pricing["final_amount"].as_float() == 0)
        )
        return await self.session.scalar(stmt) or 0

    async def get_gateway_stats(self) -> list[GatewayStatsDto]:
        now = datetime_now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = (now - timedelta(days=now.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        month_ago = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (last_month_end - timedelta(days=1)).replace(day=1)

        final_amount = Transaction.pricing["final_amount"].as_float()
        original_amount = Transaction.pricing["original_amount"].as_float()
        is_free = final_amount == 0
        is_completed = Transaction.status == TransactionStatus.COMPLETED

        stmt = select(
            Transaction.gateway_type,
            func.count().label("total_transactions"),
            func.sum(case((is_completed, 1), else_=0)).label("completed_transactions"),
            func.sum(case((is_free, 1), else_=0)).label("free_transactions"),
            func.sum(case((is_completed, final_amount), else_=0.0)).label("total_income"),
            func.sum(
                case(
                    (
                        and_(is_completed, Transaction.created_at >= today_start),
                        final_amount,
                    ),
                    else_=0.0,
                )
            ).label("daily_income"),
            func.sum(
                case(
                    (
                        and_(is_completed, Transaction.created_at >= week_ago),
                        final_amount,
                    ),
                    else_=0.0,
                )
            ).label("weekly_income"),
            func.sum(
                case(
                    (
                        and_(is_completed, Transaction.created_at >= month_ago),
                        final_amount,
                    ),
                    else_=0.0,
                )
            ).label("monthly_income"),
            func.sum(
                case(
                    (
                        and_(
                            is_completed,
                            Transaction.created_at >= last_month_start,
                            Transaction.created_at < last_month_end,
                        ),
                        final_amount,
                    ),
                    else_=0.0,
                )
            ).label("last_month_income"),
            func.sum(case((and_(is_completed, ~is_free), 1), else_=0)).label("paid_count"),
            func.sum(case((and_(is_completed, ~is_free), 1), else_=0)).label("paid_count"),
            func.sum(case((is_completed, original_amount - final_amount), else_=0.0)).label(
                "total_discounts"
            ),
        ).group_by(Transaction.gateway_type)

        result = await self.session.execute(stmt)
        rows = result.mappings().all()

        logger.debug(f"Gateway stats fetched for {len(rows)} gateways")
        return [
            GatewayStatsDto(
                gateway_type=row["gateway_type"],
                total_income=Decimal(row["total_income"] or 0),
                daily_income=Decimal(row["daily_income"] or 0),
                weekly_income=Decimal(row["weekly_income"] or 0),
                monthly_income=Decimal(row["monthly_income"] or 0),
                last_month_income=Decimal(row["last_month_income"] or 0),
                paid_count=int(row["paid_count"] or 0),
                total_discounts=Decimal(row["total_discounts"] or 0),
                total_transactions=int(row["total_transactions"] or 0),
                completed_transactions=int(row["completed_transactions"] or 0),
                free_transactions=int(row["free_transactions"] or 0),
            )
            for row in rows
        ]

    async def get_plan_income(self) -> list[PlanIncomeDto]:
        plan_id_expr = Transaction.plan_snapshot["id"].as_integer()
        final_amount_expr = Transaction.pricing["final_amount"].as_float()

        stmt = (
            select(
                plan_id_expr.label("plan_id"),
                Transaction.currency.label("currency"),
                func.sum(final_amount_expr).label("total_income"),
            )
            .where(
                Transaction.status == TransactionStatus.COMPLETED,
                plan_id_expr.isnot(None),
            )
            .group_by(plan_id_expr, Transaction.currency)
        )

        result = await self.session.execute(stmt)
        logger.debug("Plan income stats fetched")
        return [
            PlanIncomeDto(
                plan_id=row["plan_id"],
                currency=row["currency"].symbol,
                total_income=float(row["total_income"] or 0),
            )
            for row in result.mappings()
        ]

    async def get_recent_pending(
        self,
        user_id: int,
        plan_id: int,
        duration_days: int,
        gateway_type: PaymentGatewayType,
    ) -> Optional[TransactionDto]:
        threshold = datetime_now() - timedelta(minutes=15)
        stmt = (
            select(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.gateway_type == gateway_type,
                Transaction.status == TransactionStatus.PENDING,
                Transaction.plan_snapshot["id"].as_integer() == plan_id,
                Transaction.plan_snapshot["duration"].as_integer() == duration_days,
                Transaction.created_at >= threshold,
            )
            .order_by(Transaction.created_at.desc())
            .limit(1)
        )
        db_transaction = await self.session.scalar(stmt)

        if db_transaction:
            logger.debug(
                f"Found recent pending transaction for user_id '{user_id}', "
                f"plan_id '{plan_id}', duration '{duration_days}'"
            )
            return self._convert_to_dto(db_transaction)

        logger.debug(
            f"No recent pending transaction for user_id '{user_id}', "
            f"plan_id '{plan_id}', duration '{duration_days}'"
        )
        return None

    async def get_user_payment_stats(
        self,
        user_id: int,
    ) -> tuple[Optional[datetime], list[UserPaymentStatsDto]]:
        last_payment_stmt = (
            select(Transaction.created_at)
            .where(
                Transaction.user_id == user_id,
                Transaction.status == TransactionStatus.COMPLETED,
            )
            .order_by(Transaction.created_at.desc())
            .limit(1)
        )

        amounts_stmt = (
            select(
                Transaction.currency.label("currency"),
                func.sum(Transaction.pricing["final_amount"].as_float()).label("total_amount"),
            )
            .where(
                Transaction.user_id == user_id,
                Transaction.status == TransactionStatus.COMPLETED,
                Transaction.pricing["final_amount"].as_float() > 0,
            )
            .group_by(Transaction.currency)
        )

        last_payment_at = await self.session.scalar(last_payment_stmt)
        amounts_rows = (await self.session.execute(amounts_stmt)).mappings().all()

        return last_payment_at, [
            UserPaymentStatsDto(
                currency=row["currency"].symbol,
                total_amount=float(row["total_amount"] or 0),
            )
            for row in amounts_rows
        ]

    async def admin_payments_page(self, query: AdminPaymentsQuery) -> AdminPaymentsPage:
        """
        Страница платежей для админки: платёж и его владелец одним запросом,
        счётчики вкладок по статусам и сумма оплаченного в рублях.
        """
        amount = sql_cast(Transaction.pricing["final_amount"].astext, Numeric)
        statuses = {
            "completed": Transaction.status == TransactionStatus.COMPLETED,
            "failed": Transaction.status == TransactionStatus.FAILED,
            "pending": Transaction.status == TransactionStatus.PENDING,
            "canceled": Transaction.status == TransactionStatus.CANCELED,
            "refunded": Transaction.status == TransactionStatus.REFUNDED,
        }

        filters = self._admin_payment_filters(query)

        def joined(stmt):  # type: ignore[no-untyped-def]
            return (
                stmt.select_from(Transaction)
                .join(User, User.id == Transaction.user_id)
                .where(*filters)
            )

        paid = func.coalesce(
            func.sum(amount).filter(
                Transaction.status == TransactionStatus.COMPLETED,
                Transaction.currency == Currency.RUB,
            ),
            0,
        )
        cols = [func.count().label("all"), paid.label("paid_rub")] + [
            func.count().filter(cond).label(name) for name, cond in statuses.items()
        ]
        counts = dict((await self.session.execute(joined(select(*cols)))).one()._mapping)
        paid_rub = Decimal(counts.pop("paid_rub") or 0)

        stmt = joined(select(Transaction, User.telegram_id, User.name, User.username))
        if query.status != "all":
            stmt = stmt.where(statuses[query.status])
        per_page = max(1, min(query.per_page, 100))
        stmt = (
            stmt.order_by(Transaction.created_at.desc(), Transaction.id.desc())
            .offset((max(1, query.page) - 1) * per_page)
            .limit(per_page)
        )

        rows = []
        for t, telegram_id, name, username in (await self.session.execute(stmt)).all():
            pricing = t.pricing or {}
            snapshot = t.plan_snapshot or {}
            rows.append(
                AdminPaymentRow(
                    payment_id=t.payment_id,
                    status=str(t.status),
                    purchase_type=str(t.purchase_type),
                    gateway_type=str(t.gateway_type),
                    currency=str(t.currency),
                    original_amount=_text(pricing.get("original_amount")),
                    discount_percent=pricing.get("discount_percent"),
                    final_amount=_text(pricing.get("final_amount")),
                    plan_name=snapshot.get("name"),
                    duration_days=snapshot.get("duration"),
                    extra_devices=snapshot.get("extra_devices") or 0,
                    is_test=t.is_test,
                    is_gift=t.is_gift,
                    created_at=t.created_at,
                    updated_at=t.updated_at,
                    telegram_id=telegram_id,
                    user_name=name or "",
                    username=username,
                )
            )

        total = counts["all"] if query.status == "all" else counts[query.status]
        return AdminPaymentsPage(rows=rows, total=total, counts=counts, paid_rub=paid_rub)

    @classmethod
    def _admin_payment_filters(cls, query: AdminPaymentsQuery) -> list:  # type: ignore[type-arg]
        filters = []
        if not query.include_test:
            filters.append(Transaction.is_test.is_(False))
        if query.gateway:
            filters.append(Transaction.gateway_type == query.gateway)
        if query.purchase_type:
            filters.append(Transaction.purchase_type == query.purchase_type)
        if query.date_from:
            filters.append(Transaction.created_at >= query.date_from)
        if query.date_to:
            filters.append(Transaction.created_at < query.date_to)
        if query.payment_id:
            filters.append(Transaction.payment_id == query.payment_id)
        elif query.q.strip():
            filters.append(cls._admin_client_condition(query.q))
        return filters

    @staticmethod
    def _admin_client_condition(q: str):  # type: ignore[no-untyped-def]
        """Чьи платежи: tg id (в том числе `rs_…`) или имя/ник."""
        term = q.strip()
        if term.lower().startswith("rs_"):
            term = term[3:]
        term = term.lstrip("@")
        if term.lstrip("-").isdigit():
            return User.telegram_id == int(term)
        if len(term) >= 2:
            pattern = f"%{term}%"
            return or_(User.name.ilike(pattern), User.username.ilike(pattern))
        return false()

    async def get_by_payment_ids(self, payment_ids: list[UUID]) -> list[TransactionDto]:
        if not payment_ids:
            return []
        stmt = select(Transaction).where(Transaction.payment_id.in_(payment_ids))
        result = await self.session.scalars(stmt)
        return self._convert_to_dto_list(cast(list, result.all()))

    async def admin_metrics(self, days: int) -> dict[str, Any]:
        """
        Цифры для админки: выручка, новые и продления, отток, истекающие,
        конверсия пробного периода, источник оплат. Только агрегаты.

        «Деньги» — завершённые не тестовые платежи в рублях с ненулевой
        суммой: бесплатные активации выручкой не считаем. Дни и месяцы — по
        Москве: по ней живёт бизнес, и сутки по UTC резали бы вечер.
        """
        now = datetime_now()
        since = now - timedelta(days=days)
        params = {"since": since, "now": now}

        async def rows(sql: str, **extra: Any) -> list[Any]:
            result = await self.session.execute(text(_PAID_CTE + sql), {**params, **extra})
            return list(result.all())

        daily = await rows(
            """
            SELECT (created_at AT TIME ZONE 'Europe/Moscow')::date AS day, purchase_type,
                   sum(amount) AS amount, count(*) AS payments
            FROM paid WHERE created_at >= :since
            GROUP BY 1, 2 ORDER BY 1
            """
        )
        monthly = await rows(
            """
            SELECT to_char(
                       date_trunc('month', created_at AT TIME ZONE 'Europe/Moscow'), 'YYYY-MM'
                   ) AS month,
                   sum(amount) AS amount, count(*) AS payments,
                   count(DISTINCT user_id) AS clients
            FROM paid WHERE created_at >= :now - interval '12 months'
            GROUP BY 1 ORDER BY 1
            """
        )
        totals = (await rows(
            """
            SELECT count(*) AS payments, coalesce(sum(amount), 0) AS amount,
                   count(DISTINCT user_id) AS clients,
                   count(*) FILTER (WHERE purchase_type = 'RENEW') AS renewals,
                   (SELECT count(*) FROM (
                        SELECT user_id, min(created_at) AS first FROM paid GROUP BY user_id
                    ) f WHERE f.first >= :since) AS new_clients
            FROM paid WHERE created_at >= :since
            """
        ))[0]
        sources = await rows(
            """
            SELECT CASE WHEN p.source IS NOT NULL THEN p.source
                        WHEN u.telegram_id < 0 THEN 'web'
                        ELSE 'unknown' END AS source,
                   count(*) AS payments, sum(p.amount) AS amount
            FROM paid p JOIN users u ON u.id = p.user_id
            WHERE p.created_at >= :since
            GROUP BY 1
            """
        )
        subs = (await self.session.execute(text(
            """
            SELECT
              count(*) FILTER (
                  WHERE s.status = 'ACTIVE' AND NOT s.is_trial
                    AND s.expire_at > :now AND s.expire_at <= :now + interval '3 days'
              ) AS expiring_3,
              count(*) FILTER (
                  WHERE s.status = 'ACTIVE' AND NOT s.is_trial
                    AND s.expire_at > :now AND s.expire_at <= :now + interval '7 days'
              ) AS expiring_7,
              count(*) FILTER (
                  WHERE s.status = 'ACTIVE' AND NOT s.is_trial AND s.expire_at > :now
              ) AS active_paid,
              count(*) FILTER (
                  WHERE s.status = 'ACTIVE' AND s.is_trial AND s.expire_at > :now
              ) AS active_trial,
              count(*) FILTER (WHERE NOT s.is_trial AND s.status <> 'DELETED'
                               AND s.expire_at >= :since AND s.expire_at < :now) AS lapsed
            FROM users u JOIN subscriptions s ON s.id = u.current_subscription_id
            """
        ), params)).one()
        trials = await rows(
            """
            , trials AS (
                SELECT user_id, min(created_at) AS started FROM subscriptions
                WHERE is_trial GROUP BY user_id
            )
            SELECT to_char(
                       date_trunc('month', t.started AT TIME ZONE 'Europe/Moscow'), 'YYYY-MM'
                   ) AS month,
                   count(*) AS trials,
                   count(*) FILTER (WHERE EXISTS (
                       SELECT 1 FROM paid p WHERE p.user_id = t.user_id AND p.created_at > t.started
                   )) AS converted
            FROM trials t WHERE t.started >= :now - interval '6 months'
            GROUP BY 1 ORDER BY 1
            """
        )

        by_day: dict[str, dict[str, Any]] = {}
        for day, kind, amount, count in daily:
            entry = by_day.setdefault(
                str(day), {"day": str(day), "amount": Decimal(0), "payments": 0, "by_type": {}}
            )
            entry["amount"] += amount
            entry["payments"] += count
            entry["by_type"][str(kind)] = str(amount)

        return {
            "days": days,
            "since": since,
            "daily": [{**d, "amount": str(d["amount"])} for d in by_day.values()],
            "monthly": [
                {"month": m, "amount": str(a), "payments": p, "clients": c}
                for m, a, p, c in monthly
            ],
            "totals": {
                "payments": totals.payments,
                "amount": str(totals.amount),
                "clients": totals.clients,
                "renewals": totals.renewals,
                "new_clients": totals.new_clients,
            },
            "sources": {s: {"payments": p, "amount": str(a)} for s, p, a in sources},
            "subscriptions": dict(subs._mapping),
            "trials": [{"month": m, "trials": t, "converted": c} for m, t, c in trials],
        }


def _text(value) -> Optional[str]:  # type: ignore[no-untyped-def]
    return None if value is None else str(value)


# Платежи, которые считаются деньгами. Источник берём из колонки, а у
# старых платежей без неё — по клиенту: у кого нет телеграма, тот платил
# на сайте.
_PAID_CTE = """
WITH paid AS (
    SELECT t.user_id, t.created_at, t.purchase_type, t.source,
           (t.pricing ->> 'final_amount')::numeric AS amount
    FROM transactions t
    WHERE t.status = 'COMPLETED' AND NOT t.is_test AND t.currency = 'RUB'
      AND (t.pricing ->> 'final_amount')::numeric > 0
)
"""
