import httpx
from dishka.integrations.taskiq import FromDishka, inject
from loguru import logger

from src.core.config import AppConfig
from src.infrastructure.taskiq.broker import broker


@broker.task()
@inject(patch_module=True)
async def create_moy_nalog_receipt_task(
    payment_id: str,
    amount: float,
    description: str,
    operation_time: str,
    config: FromDishka[AppConfig],
) -> None:
    url = config.moy_nalog_service_url
    key = config.moy_nalog_service_key

    if not url or not key:
        logger.debug("Moy Nalog service not configured, skipping receipt")
        return

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{url}/receipt",
                json={
                    "payment_id": payment_id,
                    "amount": amount,
                    "description": description,
                    "operation_time": operation_time,
                },
                headers={"X-Service-Key": key},
            )
        logger.info(
            f"Moy Nalog receipt queued for '{payment_id}': "
            f"HTTP {resp.status_code} {resp.text[:200]}"
        )
    except Exception as e:
        # Non-critical: receipt service handles its own retry queue.
        # If the service is temporarily down, the receipt will be missing from the queue.
        logger.error(f"Failed to reach Moy Nalog service for '{payment_id}': {e}")
