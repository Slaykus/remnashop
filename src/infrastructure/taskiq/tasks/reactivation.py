from dishka.integrations.taskiq import FromDishka, inject

from src.application.use_cases.reactivation import SendReactivationNotifications
from src.infrastructure.taskiq.broker import broker


# Раз в сутки в 12:00 по Москве. Пояс задаём явно: сервер и контейнеры
# живут в UTC, и хранить смещение в голове — верный способ однажды
# разбудить людей письмом в три ночи. Чаще раза в день не нужно: шаги
# кампании считаются в днях.
@broker.task(
    schedule=[{"cron": "0 12 * * *", "cron_offset": "Europe/Moscow"}],
    retry_on_error=False,
)
@inject(patch_module=True)
async def send_reactivation_notifications_task(
    send_reactivation: FromDishka[SendReactivationNotifications],
) -> None:
    await send_reactivation.system()
