from dataclasses import dataclass
from datetime import timezone
from datetime import datetime
from uuid import UUID

from loguru import logger

from src.application.common import Interactor, Notifier, Remnawave
from src.application.common.dao import SubscriptionDao
from src.application.common.dao.yandex_quota import YandexQuotaDao
from src.application.common.uow import UnitOfWork
from src.application.dto import UserDto
from src.application.dto.yandex_quota import UserYandexQuotaDto
from src.core.config import AppConfig


@dataclass(frozen=True)
class PurchaseTrafficResetDto:
    user: UserDto


class PurchaseTrafficReset(Interactor[PurchaseTrafficResetDto, None]):
    required_permission = None

    def __init__(
        self,
        uow: UnitOfWork,
        config: AppConfig,
        quota_dao: YandexQuotaDao,
        subscription_dao: SubscriptionDao,
        remnawave: Remnawave,
        notifier: Notifier,
    ) -> None:
        self.uow = uow
        self.config = config
        self.quota_dao = quota_dao
        self.subscription_dao = subscription_dao
        self.remnawave = remnawave
        self.notifier = notifier

    async def _execute(self, actor: UserDto, data: PurchaseTrafficResetDto) -> None:
        user = data.user
        yandex = self.config.yandex

        if not yandex.enabled or not yandex.squad_uuid:
            logger.warning(f"[YandexQuota] Traffic reset purchased by {user.telegram_id} but feature disabled")
            return

        now = datetime.now(timezone.utc)
        squad_uuid = UUID(yandex.squad_uuid)

        quota = await self.quota_dao.get_by_telegram_id(user.telegram_id)
        if quota is None:
            quota = UserYandexQuotaDto(
                user_telegram_id=user.telegram_id,
                period_start=now.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
            )

        # Restore squad access if user was restricted
        if quota.is_restricted:
            sub = await self.subscription_dao.get_current(user.telegram_id)
            if sub and sub.user_remna_id:
                try:
                    await self.remnawave.update_user_squads(sub.user_remna_id, add_squad=squad_uuid)
                except Exception as e:
                    logger.error(f"[YandexQuota] Failed to restore squad for {user.telegram_id}: {e}")
            quota.is_restricted = False
            quota.restricted_at = None

        quota.reset_baseline_bytes += quota.used_bytes
        quota.used_bytes = 0
        quota.warned_at = None

        await self.quota_dao.upsert(quota)
        await self.uow.commit()

        logger.info(f"[YandexQuota] Traffic reset purchased by user {user.telegram_id}, new baseline={quota.reset_baseline_bytes}")

        await self.notifier.notify_user(user, i18n_key="ntf-yandex.reset-purchased")
