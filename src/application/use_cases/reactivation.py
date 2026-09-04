from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum, auto
from typing import Optional

from loguru import logger

from src.application.common import EventPublisher, Interactor
from src.application.common.dao import NotificationLogDao, SettingsDao, UserDao
from src.application.common.uow import UnitOfWork
from src.application.dto import UserDto
from src.application.events import ReactivationEvent
from src.core.config import AppConfig
from src.core.constants import T_ME


class Keyboard(StrEnum):
    """Какая клавиатура у письма. Строкой, а не готовым объектом: собрать
    её можно только в момент отправки — адрес поддержки берётся из
    настроек бота."""

    MENU = auto()
    BUY = auto()
    RENEW_AND_SUPPORT = auto()


@dataclass(frozen=True)
class ReactivationStep:
    """Одно письмо кампании.

    `grant` и `show` разведены намеренно. Скидка выдаётся только на первом
    касании; напоминание приходит, пока она ещё жива, и её же называет, но
    заново не выдаёт — скидка, которую дают дважды, перестаёт быть поводом
    торопиться.
    """

    kind: str
    segment: str
    i18n_key: str
    day: int
    keyboard: Keyboard
    grant: int = 0
    show: int = 0


REACTIVATION_STEPS: tuple[ReactivationStep, ...] = (
    # Не забравшим пробник — в меню, а не на экран покупки: бесплатная
    # неделя лежит там, и платить им пока незачем.
    ReactivationStep(
        "TRIAL_UNUSED_D2", "never", "ntf-reactivation.trial-unused-first", 2, Keyboard.MENU
    ),
    ReactivationStep(
        "TRIAL_UNUSED_D7", "never", "ntf-reactivation.trial-unused-last", 7, Keyboard.MENU
    ),
    ReactivationStep(
        "TRIAL_EXPIRED_D3", "trial", "ntf-reactivation.trial-expired-offer", 3,
        Keyboard.BUY, grant=20, show=20,
    ),
    ReactivationStep(
        "TRIAL_EXPIRED_D5", "trial", "ntf-reactivation.trial-expired-last", 5,
        Keyboard.BUY, show=20,
    ),
    ReactivationStep(
        "PAID_EXPIRED_D3", "paid", "ntf-reactivation.paid-expired-offer", 3,
        Keyboard.RENEW_AND_SUPPORT, grant=30, show=30,
    ),
    ReactivationStep(
        "PAID_EXPIRED_D5", "paid", "ntf-reactivation.paid-expired-last", 5,
        Keyboard.RENEW_AND_SUPPORT, show=30,
    ),
)

DISCOUNT_DAYS = 3


@dataclass
class ReactivationReport:
    """Что задача сделала или сделала бы. Возвращается для лога и проверки."""

    dry_run: bool
    considered: int = 0
    planned: dict[str, int] = None  # type: ignore[assignment]
    sent: int = 0
    skipped_already_sent: int = 0

    def __post_init__(self) -> None:
        if self.planned is None:
            self.planned = {}


class SendReactivationNotifications(Interactor[None, ReactivationReport]):
    """
    Письма тем, кто не забрал пробник или остался с истёкшей подпиской.

    Задача выключена по умолчанию и по умолчанию же в сухом режиме: письма
    уходят живым людям, и решение отправлять принимает человек, а не
    значение по умолчанию.
    """

    required_permission = None

    def __init__(
        self,
        uow: UnitOfWork,
        config: AppConfig,
        user_dao: UserDao,
        settings_dao: SettingsDao,
        notification_log_dao: NotificationLogDao,
        event_bus: EventPublisher,
    ) -> None:
        self.uow = uow
        self.config = config
        self.user_dao = user_dao
        self.settings_dao = settings_dao
        self.notification_log_dao = notification_log_dao
        self.event_bus = event_bus

    async def _execute(self, actor: UserDto, data: None) -> ReactivationReport:
        settings = await self.settings_dao.get()
        if not settings.extra.reactivation_enabled:
            logger.debug("[Reactivation] Campaign is off, nothing to do")
            return ReactivationReport(dry_run=True)

        dry_run = settings.extra.reactivation_dry_run
        report = ReactivationReport(dry_run=dry_run)

        candidates = await self.user_dao.get_reactivation_candidates()
        report.considered = len(candidates)

        for step in REACTIVATION_STEPS:
            already = await self.notification_log_dao.sent_user_ids(step.kind)
            # Окно в двое суток: задача ходит раз в день, но пропущенный
            # запуск не должен лишать человека письма навсегда.
            matched = [
                row
                for row in candidates
                if row["segment"] == step.segment
                and step.day <= row["days"] <= step.day + 1
                and row["id"] not in already
            ]
            report.planned[step.kind] = len(matched)

            for row in matched:
                if dry_run:
                    logger.info(
                        f"[Reactivation] DRY RUN: would send '{step.kind}' to user "
                        f"'{row['telegram_id']}' (grant={step.grant}%)"
                    )
                    continue
                await self._deliver(row, step, report)

        logger.info(
            f"[Reactivation] {'dry run' if dry_run else 'run'}: "
            f"considered={report.considered}, planned={report.planned}, sent={report.sent}"
        )
        return report

    async def _deliver(
        self,
        row: dict,
        step: ReactivationStep,
        report: ReactivationReport,
    ) -> None:
        user = await self.user_dao.get_by_id(row["id"])
        if user is None:
            return

        expires_at: Optional[datetime] = None
        async with self.uow:
            # Журнал пишем до отправки: если письмо не уйдёт, человек
            # останется без него, и это лучше, чем получить два.
            if not await self.notification_log_dao.mark_sent(
                user.id or 0,
                step.kind,
                details={"grant": step.grant} if step.grant else None,
            ):
                report.skipped_already_sent += 1
                return

            if step.grant:
                expires_at = datetime.now(timezone.utc) + timedelta(days=DISCOUNT_DAYS)
                user.purchase_discount = step.grant
                user.purchase_discount_expires_at = expires_at
                await self.user_dao.update(user)

            await self.uow.commit()

        support_url = f"{T_ME}{self.config.bot.support_username.get_secret_value()}"
        await self.event_bus.publish(
            ReactivationEvent(
                user=user,
                i18n_key=step.i18n_key,
                keyboard=step.keyboard.value,
                support_url=support_url,
                discount=step.show,
                days=DISCOUNT_DAYS,
            )
        )
        report.sent += 1
        logger.info(f"[Reactivation] Sent '{step.kind}' to user '{user.telegram_id}'")
