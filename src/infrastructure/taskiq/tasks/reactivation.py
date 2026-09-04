from dishka.integrations.taskiq import FromDishka, inject

from src.application.use_cases.reactivation import SendReactivationNotifications
from src.infrastructure.taskiq.broker import broker


# Раз в сутки в 12:00 UTC — днём по Москве. Ночью писать людям незачем, а
# чаще раза в день кампании возврата не нужно: шаги считаются в днях.
@broker.task(schedule=[{"cron": "0 12 * * *"}], retry_on_error=False)
@inject(patch_module=True)
async def send_reactivation_notifications_task(
    send_reactivation: FromDishka[SendReactivationNotifications],
) -> None:
    await send_reactivation.system()
