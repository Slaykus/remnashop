from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

from loguru import logger

from src.application.common import EventPublisher, Interactor, Remnawave
from src.application.common.dao import PlanDao, SubscriptionDao, UserDao
from src.application.common.uow import UnitOfWork
from src.application.use_cases.ad_link.commands.process_click import (
    ApplyPendingAdBonus,
    ApplyPendingAdBonusDto,
)
from src.application.dto import PlanSnapshotDto, SubscriptionDto, TransactionDto, UserDto
from src.application.events import TrialActivatedEvent
from src.core.enums import PurchaseType, SubscriptionStatus
from src.core.exceptions import TrialNotAvailableError
from src.core.types import RemnaUserDto
from src.core.utils.converters import days_to_datetime
from src.core.utils.i18n_helpers import (
    i18n_format_days,
    i18n_format_device_limit,
    i18n_format_traffic_limit,
)
from src.core.utils.time import datetime_now


@dataclass(frozen=True)
class ActivateTrialSubscriptionDto:
    user: UserDto
    plan: PlanSnapshotDto


class ActivateTrialSubscription(Interactor[ActivateTrialSubscriptionDto, None]):
    required_permission = None

    def __init__(
        self,
        uow: UnitOfWork,
        user_dao: UserDao,
        subscription_dao: SubscriptionDao,
        remnawave: Remnawave,
        event_publisher: EventPublisher,
    ) -> None:
        self.uow = uow
        self.user_dao = user_dao
        self.subscription_dao = subscription_dao
        self.remnawave = remnawave
        self.event_publisher = event_publisher

    async def _execute(self, actor: UserDto, data: ActivateTrialSubscriptionDto) -> None:
        user = data.user
        plan = data.plan

        if not user.is_trial_available:
            raise TrialNotAvailableError(f"Trial not available for user '{user.remna_name}'")

        logger.info(f"{actor.log} Started trial for user '{user.id}'")

        created_user = await self.remnawave.create_user(user, plan=plan)

        trial_subscription = SubscriptionDto(
            user_remna_id=created_user.uuid,
            status=SubscriptionStatus(created_user.status),
            is_trial=True,
            traffic_limit=plan.traffic_limit,
            device_limit=plan.device_limit,
            traffic_limit_strategy=plan.traffic_limit_strategy,
            tag=plan.tag,
            internal_squads=plan.internal_squads,
            external_squad=plan.external_squad,
            expire_at=created_user.expire_at,
            url=created_user.subscription_url,
            plan_snapshot=plan,
        )

        async with self.uow:
            await self.subscription_dao.create(
                subscription=trial_subscription,
                user_id=user.id,
            )
            await self.user_dao.set_trial_available(user.id, False)
            await self.uow.commit()

        logger.debug(f"{actor.log} Created new trial subscription for user '{user.id}'")

        event = TrialActivatedEvent(
            telegram_id=user.telegram_id,
            username=user.username,
            name=user.name,
            email=user.email,
            plan_name=(plan.name, {}),
            plan_type=plan.type,
            plan_traffic_limit=i18n_format_traffic_limit(plan.traffic_limit),
            plan_device_limit=i18n_format_device_limit(plan.device_limit),
            plan_duration=i18n_format_days(plan.duration),
        )
        await self.event_publisher.publish(event)
        logger.info(
            f"{actor.log} Trial subscription completed successfully for user '{user.remna_name}'"
        )


@dataclass(frozen=True)
class PurchaseSubscriptionDto:
    user: UserDto
    transaction: TransactionDto
    subscription: Optional[SubscriptionDto]


class PurchaseSubscription(Interactor[PurchaseSubscriptionDto, None]):
    required_permission = None

    def __init__(
        self,
        uow: UnitOfWork,
        user_dao: UserDao,
        subscription_dao: SubscriptionDao,
        remnawave: Remnawave,
    ) -> None:
        self.uow = uow
        self.user_dao = user_dao
        self.subscription_dao = subscription_dao
        self.remnawave = remnawave

    async def _execute(self, actor: UserDto, data: PurchaseSubscriptionDto) -> None:  # noqa: C901
        user = data.user
        transaction = data.transaction
        subscription = data.subscription
        plan = transaction.plan_snapshot
        purchase_type = transaction.purchase_type
        has_trial = subscription.is_trial if subscription else False

        if not user or not plan:
            raise ValueError(f"User or plan not found for transaction '{transaction.id}'")

        logger.info(
            f"{actor.log} Purchase subscription started: '{purchase_type}' "
            f"for user '{user.remna_name}'"
        )

        async with self.uow:
            # 1. NEW PURCHASE (NOT TRIAL)
            if purchase_type == PurchaseType.NEW and not has_trial:
                created_user = await self.remnawave.create_user(user, plan=plan)
                new_sub = self._build_subscription_dto(created_user, plan)

                await self.subscription_dao.create(
                    subscription=new_sub,
                    user_id=user.id,
                )
                await self.user_dao.set_trial_available(user.id, False)
                if user.purchase_discount:
                    user.purchase_discount = 0
                    await self.user_dao.update(user)
                await self.uow.commit()

                logger.debug(f"{actor.log} Created new subscription for user '{user.id}'")

            # 2. RENEW (NOT TRIAL)
            elif purchase_type == PurchaseType.RENEW and not has_trial:
                if not subscription:
                    raise ValueError(
                        f"No subscription found for renewal for user '{user.remna_name}'"
                    )

                duration = transaction.plan_snapshot.duration

                if duration == 0:
                    new_expire = days_to_datetime(duration)  # unlimited
                else:
                    base_date = max(subscription.expire_at, datetime_now())
                    new_expire = base_date + timedelta(days=duration)

                subscription.expire_at = new_expire
                subscription.device_limit = plan.device_limit
                subscription.traffic_limit = plan.traffic_limit
                subscription.traffic_limit_strategy = plan.traffic_limit_strategy
                subscription.tag = plan.tag
                subscription.internal_squads = plan.internal_squads
                subscription.external_squad = plan.external_squad

                await self.remnawave.update_user(
                    user=user,
                    uuid=subscription.user_remna_id,
                    subscription=subscription,
                    reset_traffic=True,
                )

                subscription.plan_snapshot = plan
                await self.subscription_dao.update(subscription)
                if user.purchase_discount:
                    user.purchase_discount = 0
                    await self.user_dao.update(user)
                await self.uow.commit()
                logger.debug(f"{actor.log} Renewed subscription for user '{user.id}'")

            # 3. CHANGE OR CONVERT FROM TRIAL
            elif purchase_type == PurchaseType.CHANGE or has_trial:
                if not subscription:
                    raise ValueError(
                        f"No subscription found for change for user '{user.remna_name}'"
                    )

                await self.subscription_dao.update_status(
                    subscription_id=subscription.id,
                    status=SubscriptionStatus.DELETED,
                )

                updated_user = await self.remnawave.update_user(
                    user=user,
                    uuid=subscription.user_remna_id,
                    plan=plan,
                    reset_traffic=True,
                )

                new_sub = self._build_subscription_dto(updated_user, plan)
                await self.subscription_dao.create(
                    subscription=new_sub,
                    user_id=user.id,
                )

                if user.purchase_discount:
                    user.purchase_discount = 0
                    await self.user_dao.update(user)
                await self.uow.commit()
                logger.debug(f"{actor.log} Changed subscription for user '{user.id}'")

            else:
                raise ValueError(
                    f"Unknown purchase type '{purchase_type}' for user '{user.remna_name}'"
                )

        logger.info(f"{actor.log} Purchase subscription completed for user '{user.id}'")

    def _build_subscription_dto(
        self,
        remna_user: RemnaUserDto,
        plan: PlanSnapshotDto,
    ) -> SubscriptionDto:
        return SubscriptionDto(
            user_remna_id=remna_user.uuid,
            status=SubscriptionStatus(remna_user.status),
            is_trial=plan.is_trial,
            traffic_limit=plan.traffic_limit,
            device_limit=plan.device_limit,
            traffic_limit_strategy=plan.traffic_limit_strategy,
            tag=plan.tag,
            internal_squads=plan.internal_squads,
            external_squad=plan.external_squad,
            expire_at=remna_user.expire_at,
            url=remna_user.subscription_url,
            plan_snapshot=plan,
        )


@dataclass(frozen=True)
class ActivateFreePlanDto:
    telegram_id: int
    # Тег пробного плана. Нужен, чтобы сайт мог выдавать свой короткий
    # пробный период, не меняя тот, что бот даёт своим пользователям:
    # активных пробных планов может быть несколько.
    plan_tag: str | None = None


class ActivateFreePlan(Interactor[ActivateFreePlanDto, SubscriptionDto]):
    """Silent trial activation for Internal API — no Telegram events, just creates and returns."""

    required_permission = None

    def __init__(
        self,
        uow: UnitOfWork,
        user_dao: UserDao,
        subscription_dao: SubscriptionDao,
        plan_dao: PlanDao,
        remnawave: Remnawave,
        apply_ad_bonus: ApplyPendingAdBonus,
    ) -> None:
        self.uow = uow
        self.user_dao = user_dao
        self.subscription_dao = subscription_dao
        self.plan_dao = plan_dao
        self.remnawave = remnawave
        self.apply_ad_bonus = apply_ad_bonus

    async def _execute(self, actor: UserDto, data: ActivateFreePlanDto) -> SubscriptionDto:
        user = await self.user_dao.get_by_telegram_id(data.telegram_id)
        if not user:
            raise ValueError("User not found")
        if not user.is_trial_available:
            raise ValueError("Trial already used")

        if data.plan_tag:
            # Пробный план в боте может быть только один, поэтому короткий
            # период для сайта заводится обычным планом с доступом по ссылке.
            # Ищем по тегу среди всех активных, а не только среди пробных.
            wanted = data.plan_tag.strip().lower()
            candidates = await self.plan_dao.get_active_trial_plans()
            candidates += await self.plan_dao.get_active_plans()
            plan = next((p for p in candidates if (p.tag or "").strip().lower() == wanted), None)
            if plan is None:
                raise ValueError(f"Plan with tag '{data.plan_tag}' not found")
        else:
            plans = await self.plan_dao.get_active_trial_plans()
            if not plans:
                raise ValueError("No trial plan available")
            plan = plans[0]

        if not plan.durations:
            raise ValueError("Trial plan has no durations configured")
        plan_snapshot = PlanSnapshotDto.from_plan(plan, plan.durations[0].days)

        created_user = await self.remnawave.create_user(user, plan=plan_snapshot)

        trial_subscription = SubscriptionDto(
            user_remna_id=created_user.uuid,
            status=SubscriptionStatus(created_user.status),
            is_trial=True,
            traffic_limit=plan_snapshot.traffic_limit,
            device_limit=plan_snapshot.device_limit,
            traffic_limit_strategy=plan_snapshot.traffic_limit_strategy,
            tag=plan_snapshot.tag,
            internal_squads=plan_snapshot.internal_squads,
            external_squad=plan_snapshot.external_squad,
            expire_at=created_user.expire_at,
            url=created_user.subscription_url,
            plan_snapshot=plan_snapshot,
        )

        async with self.uow:
            await self.subscription_dao.create(
                subscription=trial_subscription,
                user_id=user.id,
            )
            await self.user_dao.set_trial_available(data.telegram_id, False)
            await self.uow.commit()

        logger.info(f"ActivateFreePlan: trial activated for telegram_id={data.telegram_id}")
        # Бонусные дни рекламной ссылки выдаются здесь, а не в момент
        # перехода: тогда подписки ещё нет, и добавлять дни не к чему.
        # Сбой выдачи не отменяет активацию — пробный период человеку
        # важнее, а недостающий бонус виден в логе.
        try:
            await self.apply_ad_bonus.system(
                ApplyPendingAdBonusDto(telegram_id=data.telegram_id)
            )
        except Exception as e:
            logger.warning(f"Не удалось выдать отложенный бонус {data.telegram_id}: {e}")

        return trial_subscription
