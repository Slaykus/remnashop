from dataclasses import dataclass

from loguru import logger

from src.application.common import EventPublisher, Interactor
from src.application.common.dao import UserDao
from src.application.common.uow import UnitOfWork
from src.application.dto import UserDto
from src.application.events import ReferralMilestoneEvent
from src.core.config import AppConfig
from src.core.config.referral_milestones import get_discount_for_tier, get_tier_for_count


@dataclass(frozen=True)
class CheckReferralMilestoneDto:
    referrer_telegram_id: int


class CheckReferralMilestone(Interactor[CheckReferralMilestoneDto, None]):
    required_permission = None

    def __init__(
        self,
        uow: UnitOfWork,
        user_dao: UserDao,
        event_publisher: EventPublisher,
        config: AppConfig,
    ) -> None:
        self.uow = uow
        self.user_dao = user_dao
        self.event_publisher = event_publisher
        self.config = config

    async def _execute(self, actor: UserDto, data: CheckReferralMilestoneDto) -> None:
        if not self.config.referral_milestones.enabled:
            return

        referrer = await self.user_dao.get_by_telegram_id(data.referrer_telegram_id)
        if not referrer:
            logger.warning(
                f"CheckReferralMilestone: referrer '{data.referrer_telegram_id}' not found"
            )
            return

        old_count = referrer.paid_referrals_count
        new_count = old_count + 1

        old_tier = get_tier_for_count(old_count)
        new_tier = get_tier_for_count(new_count)

        referrer.paid_referrals_count = new_count

        # If crossed a new tier — apply milestone discount (never lower admin discount)
        if new_tier > old_tier:
            milestone_discount = get_discount_for_tier(new_tier)
            referrer.personal_discount = max(referrer.personal_discount, milestone_discount)
            logger.info(
                f"Referrer '{referrer.telegram_id}' reached tier {new_tier} "
                f"(count={new_count}), discount={referrer.personal_discount}%"
            )

        await self.user_dao.update(referrer)
        await self.uow.commit()

        if new_tier > old_tier:
            milestone_discount = get_discount_for_tier(new_tier)
            event = ReferralMilestoneEvent(
                user=referrer,
                tier=new_tier,
                paid_referrals_count=new_count,
                discount=milestone_discount,
            )
            await self.event_publisher.publish(event)
            logger.info(
                f"Published ReferralMilestoneEvent for user '{referrer.telegram_id}' tier={new_tier}"
            )
        else:
            logger.debug(
                f"Referrer '{referrer.telegram_id}' count={new_count}, "
                f"tier unchanged ({new_tier}), no milestone event"
            )
