from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, cast
from uuid import UUID

from adaptix import Retort
from adaptix.conversion import ConversionRetort
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy import Numeric, and_, delete, false, func, or_, select, text, update
from sqlalchemy import cast as sql_cast
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.common.dao import UserDao
from src.application.dto import UserDto
from src.application.dto.admin_clients import AdminClientRow, AdminClientsPage, AdminClientsQuery
from src.core.enums import Currency, Role, SubscriptionStatus, TransactionStatus
from src.core.exceptions import AccountMergeConflictError
from src.infrastructure.database.models import (
    AdLink,
    Partner,
    PartnerEarning,
    PromocodeActivation,
    Referral,
    ReferralReward,
    Subscription,
    Transaction,
    User,
    UserOAuthProvider,
)


class UserDaoImpl(UserDao):
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

        self._convert_to_dto = self.conversion_retort.get_converter(User, UserDto)
        self._convert_to_dto_list = self.conversion_retort.get_converter(list[User], list[UserDto])

    async def create(self, user: UserDto) -> UserDto:
        user_data = self.retort.dump(user)
        user_data.pop("id", None)
        db_user = User(**user_data)

        self.session.add(db_user)
        await self.session.flush()

        logger.debug(f"New user {user.log} created in database")
        return self._convert_to_dto(db_user)

    async def get_by_id(self, user_id: int) -> Optional[UserDto]:
        stmt = select(User).where(User.id == user_id)
        db_user = await self.session.scalar(stmt)

        if db_user:
            return self._convert_to_dto(db_user)

        logger.debug(f"User id='{user_id}' not found")
        return None

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[UserDto]:
        stmt = select(User).where(User.telegram_id == telegram_id)
        db_user = await self.session.scalar(stmt)

        if db_user:
            logger.debug(f"User '{telegram_id}' found in database")
            return self._convert_to_dto(db_user)

        logger.debug(f"User '{telegram_id}' not found")
        return None

    async def get_by_remna_uuid(self, remna_uuid: UUID) -> Optional[UserDto]:
        stmt = (
            select(User)
            .join(Subscription, User.current_subscription_id == Subscription.id)
            .where(Subscription.user_remna_id == remna_uuid)
        )
        db_user = await self.session.scalar(stmt)

        if db_user:
            logger.debug(f"User with remna_uuid '{remna_uuid}' found in database")
            return self._convert_to_dto(db_user)

        logger.debug(f"User with remna_uuid '{remna_uuid}' not found")
        return None

    async def get_by_email(self, email: str) -> Optional[UserDto]:
        stmt = select(User).where(User.email == email)
        db_user = await self.session.scalar(stmt)

        if db_user:
            logger.debug(f"User with email '{email}' found in database")
            return self._convert_to_dto(db_user)

        logger.debug(f"User with email '{email}' not found")
        return None

    async def get_by_telegram_ids(self, telegram_ids: list[int]) -> list[UserDto]:
        if not telegram_ids:
            return []

        stmt = select(User).where(User.telegram_id.in_(telegram_ids))
        result = await self.session.scalars(stmt)
        db_users = cast(list, result.all())

        logger.debug(f"Retrieved '{len(db_users)}' users by telegram ID list")
        return self._convert_to_dto_list(db_users)

    async def get_by_partial_name(self, query_name: str) -> list[UserDto]:
        search_pattern = f"%{query_name}%"
        stmt = select(User).where(
            or_(
                User.name.ilike(search_pattern),
                User.username.ilike(search_pattern),
            )
        )
        result = await self.session.scalars(stmt)
        db_users = cast(list, result.all())

        logger.debug(f"Found '{len(db_users)}' users matching query '{query_name}'")
        return self._convert_to_dto_list(db_users)

    async def get_by_referral_code(self, referral_code: str) -> Optional[UserDto]:
        stmt = select(User).where(User.referral_code == referral_code)
        db_user = await self.session.scalar(stmt)

        if db_user:
            logger.debug(f"User with referral code '{referral_code}' found")
            return self._convert_to_dto(db_user)

        logger.debug(f"User with referral code '{referral_code}' not found")
        return None

    async def get_reactivation_candidates(self, max_days: int = 30) -> list[dict]:
        rows = await self.session.execute(
            text(
                """
                SELECT
                    u.id,
                    u.telegram_id,
                    u.purchase_discount,
                    CASE
                        WHEN u.current_subscription_id IS NULL THEN 'never'
                        WHEN s.is_trial THEN 'trial'
                        ELSE 'paid'
                    END AS segment,
                    CASE
                        WHEN u.current_subscription_id IS NULL
                            THEN (now()::date - u.created_at::date)
                        ELSE (now()::date - s.expire_at::date)
                    END AS days
                FROM users u
                LEFT JOIN subscriptions s ON s.id = u.current_subscription_id
                WHERE u.role = 'USER'
                  AND NOT u.is_bot_blocked
                  AND NOT u.is_blocked
                  -- Импортированным записям без привязанного телеграма
                  -- присвоен отрицательный заполнитель вместо id. Написать
                  -- им нельзя, а журнал пишется до отправки — они бы
                  -- навсегда остались помеченными как получившие письмо.
                  AND u.telegram_id > 0
                  AND (
                        (u.current_subscription_id IS NULL AND u.is_trial_available)
                     OR (s.expire_at IS NOT NULL AND s.expire_at <= now())
                  )
                """
            )
        )
        candidates = [
            {
                "id": row.id,
                "telegram_id": row.telegram_id,
                "purchase_discount": row.purchase_discount,
                "segment": row.segment,
                "days": int(row.days),
            }
            for row in rows
            if 0 <= int(row.days) <= max_days
        ]
        logger.debug(f"Found '{len(candidates)}' reactivation candidates")
        return candidates

    async def get_all(self, limit: Optional[int] = None, offset: int = 0) -> list[UserDto]:
        stmt = select(User).limit(limit).offset(offset) if limit else select(User).offset(offset)
        result = await self.session.scalars(stmt)
        db_users = cast(list, result.all())

        logger.debug(
            f"Retrieved '{len(db_users)}' users from database "
            f"with limit '{limit}' and offset '{offset}'"
        )
        return self._convert_to_dto_list(db_users)

    async def list_since(
        self,
        since: Optional[datetime] = None,
        after_id: int = 0,
        limit: int = 500,
    ) -> list[UserDto]:
        """
        Пачка users для внешнего инкрементального сбора.

        Курсор по возрастающему id, а не offset: между страницами
        дописываются новые строки, и offset начал бы их пропускать молча.
        Сортировка тоже по id — у строк, созданных одной транзакцией,
        даты совпадают, и порядок между ними не определён.

        Границу берём включительно: спрашивающий передаёт последнюю
        виденную дату, и повторно приехавшая строка ему не мешает, а вот
        потерянная — мешает.
        """
        stmt = select(User).where(User.id > after_id)

        if since is not None:
            stmt = stmt.where(User.updated_at >= since)

        stmt = stmt.order_by(User.id).limit(limit)

        result = await self.session.scalars(stmt)
        rows = cast(list, result.all())

        logger.debug(
            f"Retrieved '{len(rows)}' users changed since '{since}' "
            f"after id '{after_id}' with limit '{limit}'"
        )
        return self._convert_to_dto_list(rows)

    async def update(self, user: UserDto) -> Optional[UserDto]:
        if not user.changed_data:
            logger.debug(f"No changes detected for user '{user.id}', skipping update")
            return await self.get_by_id(user.id)

        stmt = update(User).where(User.id == user.id).values(**user.changed_data).returning(User)
        db_user = await self.session.scalar(stmt)

        if db_user:
            logger.debug(f"User '{user.id}' updated successfully with data '{user.changed_data}'")
            return self._convert_to_dto(db_user)

        logger.warning(f"Failed to update user '{user.id}'")
        return None

    async def delete(self, user_id: int) -> bool:
        stmt = delete(User).where(User.id == user_id).returning(User.id)
        result = await self.session.execute(stmt)
        deleted_id = result.scalar_one_or_none()

        if deleted_id:
            logger.debug(f"User id='{user_id}' deleted from database")
            return True

        logger.debug(f"User id='{user_id}' not found for deletion")
        return False

    async def reassign_dependents(self, from_user_id: int, to_user_id: int) -> dict[str, int]:
        """
        Передать другому аккаунту всё, что не должно исчезнуть вместе с этим.

        Вызывается при слиянии, перед удалением. Почти все ссылки на
        пользователя стоят с каскадным удалением, и удаление аккаунта молча
        уносило за собой платежи, а с ними — начисления партнёрам по этим
        платежам. Так пропали три оплаты на 1360 ₽: деньги клиенты получили,
        а подтвердить их оплату поддержка смогла только банковской справкой.

        Ничего не коммитит: всё должно лечь в одну транзакцию с удалением.
        Частичный перенос хуже отсутствия переноса — не видно, что пропало.

        Решения по таблицам:

        transactions — переносятся всегда. payment_id не трогаем: по нему
            идёт сверка со шлюзом. Начисления партнёрам висят на транзакции
            и переезжают вместе с ней.
        partner_earnings.referred_user_id — перевешивается. При удалении
            стоит SET NULL: начисление осталось бы, но без клиента.
        referral_rewards, promocode_activations — переносятся. Без
            активаций одноразовый промокод можно было бы ввести второй раз.
        ad_links.owner_user_id — перевешивается.
        referrals — человека приводят один раз. Если у настоящего аккаунта
            пригласивший уже есть, остаётся он: аккаунт старше, и его
            пригласивший пришёл первым. Связь двух аккаунтов одного человека
            друг с другом превратилась бы в приглашение самого себя — её не
            переносим, и она уходит вместе с удаляемым аккаунтом.
        user_oauth_providers — переносятся способы входа, которых у
            настоящего аккаунта ещё нет; повтор того же провайдера запрещён
            уникальным ключом.
        partners — переносится, если настоящий аккаунт не партнёр. Если
            партнёры оба, слияние отменяется: см. AccountMergeConflictError.

        Не переносится и уходит с аккаунтом: подписка (её судьбу решает
        вызывающий), счётчик трафика по псевдо-id, журналы рассылок и
        уведомлений.
        """
        moved: dict[str, int] = {}

        async def run(label: str, stmt) -> None:  # type: ignore[no-untyped-def]
            result = await self.session.execute(stmt)
            moved[label] = result.rowcount or 0  # type: ignore[attr-defined]

        # Сначала то, что может отменить слияние, — до любых изменений.
        from_partner = await self.session.scalar(
            select(Partner.id).where(Partner.user_id == from_user_id)
        )
        if from_partner is not None:
            to_partner = await self.session.scalar(
                select(Partner.id).where(Partner.user_id == to_user_id)
            )
            if to_partner is not None:
                raise AccountMergeConflictError(
                    f"Both users '{from_user_id}' and '{to_user_id}' are partners"
                )
            await run(
                "partners",
                update(Partner).where(Partner.user_id == from_user_id).values(user_id=to_user_id),
            )

        # updated_at у платежа — время последнего изменения самого платежа,
        # и по нему видно, кто его погасил: наш таймер или шлюз. Слияние
        # меняет владельца, а не платёж, так что отметку сохраняем.
        await run(
            "transactions",
            update(Transaction)
            .where(Transaction.user_id == from_user_id)
            .values(user_id=to_user_id, updated_at=Transaction.updated_at),
        )
        await run(
            "partner_earnings",
            update(PartnerEarning)
            .where(PartnerEarning.referred_user_id == from_user_id)
            .values(referred_user_id=to_user_id),
        )
        await run(
            "referral_rewards",
            update(ReferralReward)
            .where(ReferralReward.user_id == from_user_id)
            .values(user_id=to_user_id),
        )
        await run(
            "promocode_activations",
            update(PromocodeActivation)
            .where(PromocodeActivation.user_id == from_user_id)
            .values(user_id=to_user_id),
        )
        await run(
            "ad_links",
            update(AdLink)
            .where(AdLink.owner_user_id == from_user_id)
            .values(owner_user_id=to_user_id),
        )

        # Кого привёл этот человек — кроме его же второго аккаунта.
        await run(
            "referrals_as_referrer",
            update(Referral)
            .where(Referral.referrer_id == from_user_id, Referral.referred_id != to_user_id)
            .values(referrer_id=to_user_id),
        )

        # Кто привёл его — только если у настоящего аккаунта пригласившего нет.
        to_has_referrer = await self.session.scalar(
            select(Referral.id).where(Referral.referred_id == to_user_id)
        )
        if to_has_referrer is None:
            await run(
                "referrals_as_referred",
                update(Referral)
                .where(Referral.referred_id == from_user_id, Referral.referrer_id != to_user_id)
                .values(referred_id=to_user_id),
            )

        taken_providers = select(UserOAuthProvider.provider).where(
            UserOAuthProvider.user_id == to_user_id
        )
        await run(
            "oauth_providers",
            update(UserOAuthProvider)
            .where(
                and_(
                    UserOAuthProvider.user_id == from_user_id,
                    UserOAuthProvider.provider.not_in(taken_providers),
                )
            )
            .values(user_id=to_user_id),
        )

        logger.info(f"Reassigned dependents of user '{from_user_id}' to '{to_user_id}': {moved}")
        return moved

    async def exists(self, user_id: int) -> bool:
        stmt = select(select(User).where(User.id == user_id).exists())
        is_exists = await self.session.scalar(stmt) or False

        logger.debug(f"User id='{user_id}' existence status is '{is_exists}'")
        return is_exists

    async def count(self) -> int:
        stmt = select(func.count()).select_from(User)
        total = await self.session.scalar(stmt) or 0

        logger.debug(f"Total users count requested: '{total}'")
        return total

    async def filter_by_role(self, role: list[Role]) -> list[UserDto]:
        stmt = select(User)

        if isinstance(role, list):
            stmt = stmt.where(User.role.in_(role))
        else:
            stmt = stmt.where(User.role == role)

        result = await self.session.scalars(stmt)
        db_users = cast(list, result.all())

        logger.debug(f"Filtered '{len(db_users)}' users with role '{role}'")
        return self._convert_to_dto_list(db_users)

    async def set_trial_available(self, user_id: int, is_trial_available: bool) -> None:
        stmt = update(User).where(User.id == user_id).values(is_trial_available=is_trial_available)
        await self.session.execute(stmt)
        logger.debug(
            f"Trial available status for user_id '{user_id}' set to '{is_trial_available}'"
        )

    async def set_bot_blocked_status(self, user_id: int, is_bot_blocked: bool) -> None:
        stmt = update(User).where(User.id == user_id).values(is_bot_blocked=is_bot_blocked)
        await self.session.execute(stmt)
        logger.debug(f"Bot blocked status for user_id='{user_id}' set to '{is_bot_blocked}'")

    async def set_current_subscription_by_id(self, user_id: int, subscription_id: int) -> None:
        stmt = (
            update(User).where(User.id == user_id).values(current_subscription_id=subscription_id)
        )
        await self.session.execute(stmt)
        logger.debug(f"Current subscription for user_id='{user_id}' set to '{subscription_id}'")

    async def clear_current_subscription(self, user_id: int) -> None:
        stmt = update(User).where(User.id == user_id).values(current_subscription_id=None)
        await self.session.execute(stmt)
        logger.debug(f"Current subscription cleared for user_id '{user_id}'")

    async def get_blocked_users(self) -> list[UserDto]:
        stmt = select(User).where(User.is_blocked.is_(True)).order_by(User.id.desc())

        result = await self.session.execute(stmt)
        db_users = result.scalars().all()

        logger.debug(f"Retrieved '{len(db_users)}' blocked users")
        return self._convert_to_dto_list(list(db_users))

    async def get_by_ids(self, user_ids: list[int]) -> list[UserDto]:
        if not user_ids:
            return []

        stmt = select(User).where(User.id.in_(user_ids))
        result = await self.session.scalars(stmt)
        db_users = cast(list, result.all())

        logger.debug(f"Retrieved '{len(db_users)}' users by ID list")
        return self._convert_to_dto_list(db_users)

    async def get_recent_registered_users(self, limit: int = 5) -> list[UserDto]:
        stmt = select(User).order_by(User.created_at.desc()).limit(limit)

        result = await self.session.execute(stmt)
        db_users = result.scalars().all()

        logger.debug(f"Retrieved '{len(db_users)}' recently registered users")
        return self._convert_to_dto_list(list(db_users))

    async def unblock_all(self) -> None:
        stmt = update(User).where(User.is_blocked.is_(True)).values(is_blocked=False)
        await self.session.execute(stmt)
        logger.debug("All users unblocked")

    async def count_blocked(self) -> int:
        stmt = select(func.count()).select_from(User).where(User.is_blocked.is_(True))
        result = await self.session.execute(stmt)
        count = result.scalar() or 0
        logger.debug(f"Retrieved '{count}' blocked users")
        return count

    async def block_by_telegram_ids(self, telegram_ids: list[int]) -> int:
        if not telegram_ids:
            return 0
        stmt = (
            update(User)
            .where(User.telegram_id.in_(telegram_ids))
            .where(User.is_blocked.is_(False))
            .values(is_blocked=True)
            .returning(User.telegram_id)
        )
        result = await self.session.execute(stmt)
        blocked = len(result.scalars().all())
        logger.debug(f"Bulk-blocked '{blocked}' users from external blacklist")
        return blocked

    async def has_any_subscription(self, user_id: int, *, include_trial: bool = True) -> bool:
        stmt = select(func.count()).select_from(Subscription).where(Subscription.user_id == user_id)

        if not include_trial:
            stmt = stmt.where(Subscription.is_trial.is_(False))

        result = await self.session.execute(stmt)
        count = result.scalar() or 0
        return count > 0

    async def is_invited_user(self, user_id: int) -> bool:
        stmt = select(func.count()).select_from(Referral).where(Referral.referred_id == user_id)

        result = await self.session.execute(stmt)
        count = result.scalar() or 0

        is_invited = count > 0
        logger.debug(f"Checked invite status for user_id='{user_id}', result '{is_invited}'")
        return is_invited

    async def toggle_blocked_status(self, user_id: int) -> None:
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(is_blocked=~User.is_blocked)
            .returning(User.is_blocked)
        )

        result = await self.session.execute(stmt)
        new_status = result.scalar()

        logger.debug(
            f"Toggled blocked status for user_id='{user_id}', new status is '{new_status}'"
        )

    async def count_active_non_blocked(self) -> int:
        stmt = (
            select(func.count())
            .select_from(User)
            .where(User.is_blocked.is_(False), User.is_bot_blocked.is_(False))
        )
        count = await self.session.scalar(stmt) or 0
        logger.debug(f"Total active non-blocked users count is '{count}'")
        return count

    async def count_with_active_subscription(self) -> int:
        stmt = (
            select(func.count(User.id))
            .join(Subscription, User.current_subscription_id == Subscription.id)
            .where(
                User.is_blocked.is_(False),
                User.is_bot_blocked.is_(False),
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
        )
        count = await self.session.scalar(stmt) or 0
        logger.debug(f"Total users with active subscription count is '{count}'")
        return count

    async def count_with_expired_subscription(self) -> int:
        stmt = (
            select(func.count(User.id))
            .join(Subscription, User.current_subscription_id == Subscription.id)
            .where(
                User.is_blocked.is_(False),
                User.is_bot_blocked.is_(False),
                Subscription.status == SubscriptionStatus.EXPIRED,
            )
        )
        count = await self.session.scalar(stmt) or 0
        logger.debug(f"Total users with expired subscription count is '{count}'")
        return count

    async def count_with_trial_subscription(self) -> int:
        stmt = (
            select(func.count(User.id))
            .join(Subscription, User.current_subscription_id == Subscription.id)
            .where(
                User.is_blocked.is_(False),
                User.is_bot_blocked.is_(False),
                Subscription.is_trial.is_(True),
            )
        )
        count = await self.session.scalar(stmt) or 0
        logger.debug(f"Total users with trial subscription count is '{count}'")
        return count

    async def count_without_subscription(self) -> int:
        stmt = select(func.count(User.id)).where(
            User.is_blocked.is_(False),
            User.is_bot_blocked.is_(False),
            User.current_subscription_id.is_(None),
        )
        count = await self.session.scalar(stmt) or 0
        logger.debug(f"Total users without subscription count is '{count}'")
        return count

    async def get_active_non_blocked(self) -> list[UserDto]:
        stmt = select(User).where(User.is_blocked.is_(False), User.is_bot_blocked.is_(False))
        result = await self.session.scalars(stmt)
        db_users = cast(list, result.all())
        logger.debug(f"Retrieved '{len(db_users)}' active non-blocked users")
        return self._convert_to_dto_list(db_users)

    async def get_with_active_subscription(self) -> list[UserDto]:
        stmt = (
            select(User)
            .join(Subscription, User.current_subscription_id == Subscription.id)
            .where(
                User.is_blocked.is_(False),
                User.is_bot_blocked.is_(False),
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
        )
        result = await self.session.execute(stmt)
        return self._convert_to_dto_list(list(result.scalars()))

    async def get_without_subscription(self) -> list[UserDto]:
        stmt = select(User).where(
            User.is_blocked.is_(False),
            User.is_bot_blocked.is_(False),
            User.current_subscription_id.is_(None),
        )
        result = await self.session.execute(stmt)
        return self._convert_to_dto_list(list(result.scalars()))

    async def get_with_expired_subscription(self) -> list[UserDto]:
        stmt = (
            select(User)
            .join(Subscription, User.current_subscription_id == Subscription.id)
            .where(
                User.is_blocked.is_(False),
                User.is_bot_blocked.is_(False),
                Subscription.status == SubscriptionStatus.EXPIRED,
            )
        )
        result = await self.session.execute(stmt)
        return self._convert_to_dto_list(list(result.scalars()))

    async def get_with_trial_subscription(self) -> list[UserDto]:
        stmt = (
            select(User)
            .join(Subscription, User.current_subscription_id == Subscription.id)
            .where(
                User.is_blocked.is_(False),
                User.is_bot_blocked.is_(False),
                Subscription.is_trial.is_(True),
            )
        )
        result = await self.session.execute(stmt)
        return self._convert_to_dto_list(list(result.scalars()))

    async def get_active_by_plan(self, plan_id: int) -> list[UserDto]:
        stmt = (
            select(User)
            .join(Subscription, User.current_subscription_id == Subscription.id)
            .where(
                User.is_blocked.is_(False),
                User.is_bot_blocked.is_(False),
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.plan_snapshot["id"].as_integer() == plan_id,
            )
        )
        result = await self.session.execute(stmt)
        db_users = list(result.scalars().all())

        logger.debug(f"Retrieved '{len(db_users)}' active users for plan_id '{plan_id}'")
        return self._convert_to_dto_list(db_users)

    async def count_new(self, days: int) -> int:
        now = datetime.now(timezone.utc)
        if days == 0:
            since = now.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            since = now - timedelta(days=days)

        stmt = select(func.count()).select_from(User).where(User.created_at >= since)
        count = await self.session.scalar(stmt) or 0
        logger.debug(f"New users count for last {days} day(s): '{count}'")
        return count

    async def count_bot_blocked(self) -> int:
        stmt = select(func.count()).select_from(User).where(User.is_bot_blocked.is_(True))
        count = await self.session.scalar(stmt) or 0
        logger.debug(f"Total bot-blocked users count is '{count}'")
        return count

    async def admin_clients_page(self, query: AdminClientsQuery) -> AdminClientsPage:
        """
        Страница таблицы клиентов для админки: пользователь, его текущая
        подписка и сумма оплат — одним запросом, плюс счётчики вкладок.

        «Оплачено» — завершённые не тестовые платежи в рублях. Статус
        берётся с учётом срока: подписка с прошедшей датой — истёкшая, даже
        если в базе ещё ACTIVE (её закрывает фоновая задача, не сразу).
        """
        now = datetime.now(timezone.utc)
        amount = sql_cast(Transaction.pricing["final_amount"].astext, Numeric)
        paid = (
            select(
                Transaction.user_id.label("user_id"),
                func.sum(amount).label("paid"),
                func.count().label("payments"),
            )
            .where(
                Transaction.status == TransactionStatus.COMPLETED,
                Transaction.is_test.is_(False),
                Transaction.currency == Currency.RUB,
            )
            .group_by(Transaction.user_id)
            .subquery()
        )

        live = Subscription.expire_at > now
        statuses = {
            "active": and_(Subscription.status == SubscriptionStatus.ACTIVE, live),
            "expiring": and_(
                Subscription.status == SubscriptionStatus.ACTIVE,
                live,
                Subscription.expire_at <= now + timedelta(days=7),
            ),
            "trial": and_(
                Subscription.status == SubscriptionStatus.ACTIVE, live, Subscription.is_trial
            ),
            "expired": and_(
                Subscription.id.is_not(None),
                Subscription.status != SubscriptionStatus.DELETED,
                or_(Subscription.status == SubscriptionStatus.EXPIRED, ~live),
            ),
            "limited": and_(Subscription.status == SubscriptionStatus.LIMITED, live),
            "none": or_(
                Subscription.id.is_(None), Subscription.status == SubscriptionStatus.DELETED
            ),
        }

        filters = []
        if query.source == "telegram":
            filters.append(User.telegram_id > 0)
        elif query.source == "site":
            filters.append(User.telegram_id < 0)
        if query.plan_id is not None:
            filters.append(Subscription.plan_snapshot["id"].astext == str(query.plan_id))
        if query.q or query.extra_telegram_ids or query.payment_id:
            filters.append(self._admin_search_condition(query))

        def joined(stmt):  # type: ignore[no-untyped-def]
            return (
                stmt.select_from(User)
                .outerjoin(Subscription, Subscription.id == User.current_subscription_id)
                .outerjoin(paid, paid.c.user_id == User.id)
                .where(*filters)
            )

        count_cols = [func.count().label("all")] + [
            func.count().filter(cond).label(name) for name, cond in statuses.items()
        ]
        counts_row = (await self.session.execute(joined(select(*count_cols)))).one()
        counts = dict(counts_row._mapping)

        order = {
            "created": (User.created_at.desc(), User.id.desc()),
            "expire": (Subscription.expire_at.asc().nulls_last(), User.id.desc()),
            "paid": (func.coalesce(paid.c.paid, 0).desc(), User.id.desc()),
            "name": (func.lower(User.name).asc(), User.id.asc()),
        }[query.sort]

        stmt = joined(select(User, Subscription, paid.c.paid, paid.c.payments))
        if query.status != "all":
            stmt = stmt.where(statuses[query.status])
        per_page = max(1, min(query.per_page, 100))
        stmt = stmt.order_by(*order).offset((max(1, query.page) - 1) * per_page).limit(per_page)

        rows = []
        for user, sub, paid_sum, payments in (await self.session.execute(stmt)).all():
            has_sub = sub is not None and sub.status != SubscriptionStatus.DELETED
            status = None
            if has_sub:
                status = (
                    SubscriptionStatus.EXPIRED.value if sub.expire_at <= now else str(sub.status)
                )
            snapshot = sub.plan_snapshot if has_sub else {}
            rows.append(
                AdminClientRow(
                    user_id=user.id,
                    telegram_id=user.telegram_id,
                    name=user.name or "",
                    username=user.username,
                    created_at=user.created_at,
                    is_blocked=user.is_blocked,
                    is_bot_blocked=user.is_bot_blocked,
                    personal_discount=user.personal_discount or 0,
                    subscription_status=status,
                    is_trial=bool(has_sub and sub.is_trial),
                    plan_id=snapshot.get("id"),
                    plan_name=snapshot.get("name"),
                    expire_at=sub.expire_at if has_sub else None,
                    device_limit=sub.device_limit if has_sub else None,
                    paid_rub=Decimal(paid_sum or 0),
                    payments=payments or 0,
                )
            )

        total = counts["all"] if query.status == "all" else counts[query.status]
        return AdminClientsPage(rows=rows, total=total, counts=counts)

    @staticmethod
    def _admin_search_condition(query: AdminClientsQuery):  # type: ignore[no-untyped-def]
        """
        Кого ищут: по id платежа, по числу (tg id или id в боте), по имени
        или нику. Плюс найденные кабинетом по логину на сайте.
        """
        term = query.q.strip()
        if term.lower().startswith("rs_"):
            term = term[3:]
        term = term.lstrip("@")

        conds = []
        if query.payment_id:
            conds.append(
                User.id.in_(
                    select(Transaction.user_id).where(Transaction.payment_id == query.payment_id)
                )
            )
        elif term.lstrip("-").isdigit():
            number = int(term)
            conds.append(User.telegram_id == number)
            if 0 < number < 2**31:
                conds.append(User.id == number)
        elif len(term) >= 2:
            pattern = f"%{term}%"
            conds += [User.name.ilike(pattern), User.username.ilike(pattern)]
        if query.extra_telegram_ids:
            conds.append(User.telegram_id.in_(query.extra_telegram_ids))
        # Запрос в одну букву ничего не находит, а не выгружает всех.
        return or_(*conds) if conds else false()
