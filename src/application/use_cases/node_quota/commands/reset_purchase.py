from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from loguru import logger

from src.application.common import Interactor, Notifier, Remnawave
from src.application.common.dao import SubscriptionDao
from src.application.common.dao.node_quota import NodeQuotaDao
from src.application.common.uow import UnitOfWork
from src.application.dto import UserDto
from src.application.dto.message_payload import MessagePayloadDto
from src.application.dto.node_quota import UserNodeQuotaDto
from src.core.config import AppConfig
from src.core.enums import Role


@dataclass(frozen=True)
class PurchaseTrafficResetDto:
    user: UserDto


class PurchaseTrafficReset(Interactor[PurchaseTrafficResetDto, None]):
    required_permission = None

    def __init__(
        self,
        uow: UnitOfWork,
        config: AppConfig,
        quota_dao: NodeQuotaDao,
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
        node_quota = self.config.node_quota

        if not node_quota.enabled or not node_quota.squad_uuid:
            logger.warning(
                f"[NodeQuota] Traffic reset purchased by {user.telegram_id} "
                "but feature disabled"
            )
            return

        now = datetime.now(timezone.utc)
        squad_uuid = UUID(node_quota.squad_uuid)

        quota = await self.quota_dao.get_by_telegram_id(user.telegram_id)
        if quota is None:
            quota = UserNodeQuotaDto(
                user_telegram_id=user.telegram_id,
                period_start=now.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
            )

        used_bytes_before_reset = quota.used_bytes
        was_restricted = quota.is_restricted

        sub = await self.subscription_dao.get_current(user.telegram_id)
        squad_restored = False
        if sub and sub.user_remna_id:
            try:
                await self.remnawave.update_user_squads(sub.user_remna_id, add_squad=squad_uuid)
                squad_restored = True
            except Exception as e:
                logger.error(f"[NodeQuota] Failed to restore squad for {user.telegram_id}: {e}")
        else:
            logger.warning(
                f"[NodeQuota] No current subscription for paid reset user {user.telegram_id}"
            )

        if not was_restricted or squad_restored:
            quota.is_restricted = False
            quota.restricted_at = None

        quota.reset_baseline_bytes += quota.used_bytes
        quota.used_bytes = 0
        quota.warned_at = None

        await self.quota_dao.upsert(quota)
        await self.uow.commit()

        logger.info(
            f"[NodeQuota] Traffic reset purchased by user {user.telegram_id}, "
            f"new baseline={quota.reset_baseline_bytes}"
        )

        await self.notifier.notify_user(
            user,
            payload=MessagePayloadDto(i18n_key="ntf-node-quota.reset-purchased", delete_after=None),
        )

        await self.notifier.notify_admins(
            MessagePayloadDto(
                i18n_key="ntf-node-quota.reset-purchased-system",
                i18n_kwargs={
                    "telegram_id": user.telegram_id,
                    "name": user.name,
                    "username": user.username or "-",
                    "price": node_quota.reset_price_rub,
                    "used_gb": f"{used_bytes_before_reset / 1024**3:.1f}",
                    "was_restricted": int(was_restricted),
                },
                disable_default_markup=False,
                delete_after=None,
            ),
            roles=[Role.OWNER, Role.DEV, Role.ADMIN],
        )
