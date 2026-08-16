from dataclasses import dataclass
from datetime import timedelta

from loguru import logger

from src.application.common import Interactor, Notifier
from src.application.common import Remnawave
from src.application.common.dao import SubscriptionDao, UserDao
from src.application.common.dao.ad_link import AdLinkDao
from src.application.common.policy import Permission
from src.application.common.uow import UnitOfWork
from src.application.dto import UserDto
from src.application.dto.message_payload import MessagePayloadDto


@dataclass(frozen=True)
class ProcessAdClickDto:
    code: str


class ProcessAdClick(Interactor[ProcessAdClickDto, None]):
    required_permission = Permission.PUBLIC

    def __init__(
        self,
        uow: UnitOfWork,
        ad_link_dao: AdLinkDao,
        user_dao: UserDao,
        subscription_dao: SubscriptionDao,
        notifier: Notifier,
    ) -> None:
        self.uow = uow
        self.ad_link_dao = ad_link_dao
        self.user_dao = user_dao
        self.subscription_dao = subscription_dao
        self.notifier = notifier

    async def _execute(self, actor: UserDto, data: ProcessAdClickDto) -> None:
        link = await self.ad_link_dao.get_by_code(data.code)
        if not link or not link.is_active:
            logger.debug(f"[AdLink] Code '{data.code}' not found or inactive, skipping")
            return

        await self.ad_link_dao.increment_clicks(link.id)

        is_new = await self.ad_link_dao.register_user_click(link.id, actor.telegram_id)
        if not is_new:
            logger.debug(
                f"[AdLink] User {actor.telegram_id} already clicked link '{data.code}'"
            )
            return

        deferred = False
        has_bonus = link.bonus_points > 0 or link.bonus_days > 0 or link.bonus_discount_pct > 0

        if link.bonus_points > 0:
            actor.points += link.bonus_points
            await self.user_dao.update(actor)
            logger.debug(
                f"[AdLink] Granted {link.bonus_points} points to user {actor.telegram_id}"
            )

        if link.bonus_discount_pct > 0:
            actor.personal_discount = link.bonus_discount_pct
            await self.user_dao.update(actor)
            logger.debug(
                f"[AdLink] Set discount {link.bonus_discount_pct}% for user {actor.telegram_id}"
            )

        if link.bonus_days > 0:
            # get_current ждёт локальный id, а не телеграмный — для этого есть
            # отдельный метод. Из-за подмены подписка не находилась никогда, и
            # бонусные дни не выдавались ни разу за всё время.
            sub = await self.subscription_dao.get_current_by_telegram_id(actor.telegram_id)
            if sub:
                sub.expire_at = sub.expire_at + timedelta(days=link.bonus_days)
                await self.subscription_dao.update(sub)
                logger.debug(
                    f"[AdLink] Added {link.bonus_days} days to subscription "
                    f"for user {actor.telegram_id}"
                )
            else:
                # Подписки ещё нет — типичный случай для новичка. Бонус не
                # теряем: оставляем непомеченным, и он выдастся при
                # активации пробного периода.
                deferred = True
                logger.info(
                    f"[AdLink] User {actor.telegram_id} has no subscription yet, "
                    f"{link.bonus_days} bonus days deferred until activation"
                )

        if not deferred:
            await self.ad_link_dao.mark_bonus_issued(link.id, actor.telegram_id)
        await self.uow.commit()

        logger.info(
            f"[AdLink] User {actor.telegram_id} used link '{data.code}', "
            f"points={link.bonus_points}, days={link.bonus_days}, "
            f"discount={link.bonus_discount_pct}%"
        )

        if has_bonus:
            await self.notifier.notify_user(
                actor,
                payload=MessagePayloadDto(
                    i18n_key="ntf-ad.bonus-received",
                    i18n_kwargs={
                        "bonus_points": link.bonus_points,
                        "bonus_days": link.bonus_days,
                        "bonus_discount_pct": link.bonus_discount_pct,
                    },
                    delete_after=None,
                ),
            )


@dataclass(frozen=True)
class ApplyPendingAdBonusDto:
    telegram_id: int


class ApplyPendingAdBonus(Interactor[ApplyPendingAdBonusDto, int]):
    """
    Выдаёт отложенные бонусные дни, когда у человека появилась подписка.

    Бонус нельзя выдать в момент перехода по ссылке: подписки ещё нет, и
    добавлять дни не к чему — раньше они в этом случае просто пропадали.
    Причём именно у новичка, ради которого реклама и запускалась.

    Зовётся после активации пробного периода — и для пришедших из Telegram,
    и для зарегистрировавшихся на сайте: путь у них разный, а подписка
    появляется в одном и том же месте.

    Возвращает число выданных дней.
    """

    required_permission = None

    def __init__(
        self,
        uow: UnitOfWork,
        ad_link_dao: AdLinkDao,
        user_dao: UserDao,
        subscription_dao: SubscriptionDao,
        remnawave: Remnawave,
        notifier: Notifier,
    ) -> None:
        self.uow = uow
        self.ad_link_dao = ad_link_dao
        self.user_dao = user_dao
        self.subscription_dao = subscription_dao
        self.remnawave = remnawave
        self.notifier = notifier

    async def _execute(self, actor: UserDto, data: ApplyPendingAdBonusDto) -> int:
        link = await self.ad_link_dao.get_pending_bonus(data.telegram_id)
        if link is None or link.bonus_days <= 0:
            return 0

        user = await self.user_dao.get_by_telegram_id(data.telegram_id)
        subscription = await self.subscription_dao.get_current_by_telegram_id(data.telegram_id)
        if user is None or subscription is None:
            return 0

        subscription.expire_at = subscription.expire_at + timedelta(days=link.bonus_days)
        async with self.uow:
            await self.subscription_dao.update(subscription)
            # Панель обязательно: без синхронизации дни появятся в кабинете,
            # а доступ к VPN закончится в прежний срок.
            await self.remnawave.update_user(
                user=user,
                uuid=subscription.user_remna_id,
                subscription=subscription,
            )
            await self.ad_link_dao.mark_bonus_issued(link.id, data.telegram_id)
            await self.uow.commit()

        logger.info(
            f"[AdLink] Applied deferred {link.bonus_days} bonus days "
            f"from '{link.code}' to user {data.telegram_id}"
        )
        return link.bonus_days
