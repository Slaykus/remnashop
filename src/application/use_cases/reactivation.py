from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from loguru import logger

from src.application.common import Interactor, Notifier
from src.application.common.dao import NotificationLogDao, SettingsDao, UserDao
from src.application.common.uow import UnitOfWork
from src.application.dto import MessagePayloadDto, UserDto


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
    grant: int = 0
    show: int = 0


REACTIVATION_STEPS: tuple[ReactivationStep, ...] = (
    ReactivationStep("TRIAL_UNUSED_D2", "never", "ntf-reactivation.trial-unused-first", 2),
    ReactivationStep("TRIAL_UNUSED_D7", "never", "ntf-reactivation.trial-unused-last", 7),
    ReactivationStep(
        "TRIAL_EXPIRED_D3", "trial", "ntf-reactivation.trial-expired-offer", 3, grant=20, show=20
    ),
    ReactivationStep(
        "TRIAL_EXPIRED_D5", "trial", "ntf-reactivation.trial-expired-last", 5, show=20
    ),
    ReactivationStep(
        "PAID_EXPIRED_D3", "paid", "ntf-reactivation.paid-expired-offer", 3, grant=30, show=30
    ),
    ReactivationStep("PAID_EXPIRED_D5", "paid", "ntf-reactivation.paid-expired-last", 5, show=30),
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
        user_dao: UserDao,
        settings_dao: SettingsDao,
        notification_log_dao: NotificationLogDao,
        notifier: Notifier,
    ) -> None:
        self.uow = uow
        self.user_dao = user_dao
        self.settings_dao = settings_dao
        self.notification_log_dao = notification_log_dao
        self.notifier = notifier

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

        await self.notifier.notify_user(
            user,
            payload=MessagePayloadDto(
                i18n_key=step.i18n_key,
                i18n_kwargs={
                    "discount": step.show,
                    "days": DISCOUNT_DAYS,
                },
                delete_after=None,
            ),
        )
        report.sent += 1
        logger.info(f"[Reactivation] Sent '{step.kind}' to user '{user.telegram_id}'")
