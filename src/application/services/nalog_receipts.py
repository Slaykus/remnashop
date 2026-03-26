from loguru import logger

from src.application.events.system import UserPurchaseEvent
from src.core.config import AppConfig
from src.infrastructure.services.event_bus import on_event


class NalogReceiptsService:
    def __init__(self, config: AppConfig) -> None:
        self._config = config

    @on_event(UserPurchaseEvent)
    async def on_purchase(self, event: UserPurchaseEvent) -> None:
        if not self._config.moy_nalog_service_url or not self._config.moy_nalog_service_key:
            return

        # Only RUB payments, skip test and free (trial)
        if event.currency != "₽" or event.is_trial_plan:
            return

        from src.infrastructure.taskiq.tasks.receipts import create_moy_nalog_receipt_task

        logger.info(f"Queuing Moy Nalog receipt for payment '{event.payment_id}'")
        await create_moy_nalog_receipt_task.kiq(
            payment_id=str(event.payment_id),
            amount=float(event.final_amount),
            description=f"Подписка Rain VPN — {event.plan_name}",
            operation_time=event.occurred_at.isoformat(),
        )
