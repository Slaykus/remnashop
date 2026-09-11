from loguru import logger

from src.application.events.system import UserPurchaseEvent
from src.core.config import AppConfig
from src.core.utils.i18n_helpers import i18n_plain
from src.infrastructure.services.event_bus import on_event


def receipt_description(plan_name: object) -> str:
    """Строка, которую увидит человек в чеке налоговой.

    Название разворачиваем: в событии оно лежит в форме для переводов, а
    сюда должен уехать обычный текст. Отдельной функцией — чтобы её можно
    было проверить тестом, не собирая событие целиком.
    """
    return f"Подписка Rain — {i18n_plain(plan_name)}"


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
            description=receipt_description(event.plan_name),
            operation_time=event.occurred_at.isoformat(),
        )
