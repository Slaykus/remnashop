from dataclasses import dataclass
from datetime import timedelta

from loguru import logger

from src.application.common import Interactor, Notifier
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
            sub = await self.subscription_dao.get_current(actor.telegram_id)
            if sub:
                sub.expire_at = sub.expire_at + timedelta(days=link.bonus_days)
                await self.subscription_dao.update(sub)
                logger.debug(
                    f"[AdLink] Added {link.bonus_days} days to subscription "
                    f"for user {actor.telegram_id}"
                )
            else:
                logger.debug(
                    f"[AdLink] No active subscription for user {actor.telegram_id}, "
                    "bonus_days skipped"
                )

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
