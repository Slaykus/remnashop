"""
Yandex node traffic quota enforcement.

Architecture:
- Hourly: check per-user traffic on Yandex nodes via BandwidthStats API
  - Warn at 80% → send Telegram notification
  - Block at 100% → remove Yandex squad from user's active_internal_squads
  - Circuit breaker: abort if >CIRCUIT_BREAKER_PCT% of users would be restricted
- Monthly (1st of month 00:00): reset quota, restore squad access for all restricted users

Safety:
- YANDEX_DRY_RUN=true by default — logs what would happen but makes no changes
- Feature disabled entirely when YANDEX_SQUAD_UUID is not set
"""

from collections import defaultdict
from datetime import datetime, timezone
from uuid import UUID

from aiogram import Bot
from aiogram.enums import ParseMode
from dishka.integrations.taskiq import FromDishka, inject
from loguru import logger
from remnapy import RemnawaveSDK

from src.application.common import Remnawave, TranslatorRunner
from src.application.common.dao import SubscriptionDao
from src.application.common.dao.yandex_quota import YandexQuotaDao
from src.application.common.uow import UnitOfWork
from src.application.dto.yandex_quota import UserYandexQuotaDto
from src.core.config import AppConfig
from src.infrastructure.taskiq.broker import broker


def _month_start(dt: datetime) -> datetime:
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


@broker.task(schedule=[{"cron": "0 * * * *"}], retry_on_error=False)
@inject(patch_module=True)
async def check_yandex_traffic(
    config: FromDishka[AppConfig],
    sdk: FromDishka[RemnawaveSDK],
    remnawave: FromDishka[Remnawave],
    subscription_dao: FromDishka[SubscriptionDao],
    quota_dao: FromDishka[YandexQuotaDao],
    uow: FromDishka[UnitOfWork],
    bot: FromDishka[Bot],
    i18n: FromDishka[TranslatorRunner],
) -> None:
    yandex = config.yandex

    if not yandex.enabled:
        logger.debug("[YandexQuota] Feature disabled (YANDEX_SQUAD_UUID not set)")
        return

    now = datetime.now(timezone.utc)
    limit_bytes = yandex.monthly_limit_gb * 1024**3
    squad_uuid = UUID(yandex.squad_uuid)  # type: ignore[arg-type]
    dry_run = yandex.dry_run

    if dry_run:
        logger.info("[YandexQuota] DRY-RUN mode enabled — no changes will be made")

    # Collect traffic: {user_uuid_str → bytes} across all Yandex nodes
    traffic: dict[str, int] = defaultdict(int)
    month_start_iso = _month_start(now).isoformat()
    now_iso = now.isoformat()

    for node_uuid in yandex.node_uuid_list:
        try:
            result = await sdk.bandwidthstats.get_node_users_usage_legacy_stats(
                uuid=node_uuid,
                start=month_start_iso,
                end=now_iso,
            )
            for item in result.response:
                traffic[str(item.user_uuid)] += item.total
            logger.info(
                f"[YandexQuota] Node {node_uuid}: got stats for {len(result.response)} users, "
                f"total traffic: {sum(i.total for i in result.response) / 1024**3:.2f} GB"
            )
        except Exception as e:
            logger.error(f"[YandexQuota] Failed to get stats for node {node_uuid}: {e}")
            return  # Abort on any API error to avoid partial data

    active_subs = await subscription_dao.get_all_active()
    if not active_subs:
        logger.debug("[YandexQuota] No active subscriptions, nothing to check")
        return

    # Circuit breaker: abort if too many users would be blocked
    would_restrict = sum(
        1 for sub in active_subs
        if traffic.get(str(sub.user_remna_id), 0) > limit_bytes
    )
    if would_restrict > 0:
        pct = would_restrict / len(active_subs) * 100
        if pct > yandex.circuit_breaker_pct:
            logger.error(
                f"[YandexQuota] Circuit breaker: {would_restrict}/{len(active_subs)} "
                f"users ({pct:.1f}%) exceed quota. Aborting."
            )
            try:
                owner_id = config.bot.owner_id
                if owner_id:
                    await bot.send_message(
                        owner_id,
                        f"⚠️ Яндекс-квота: сработал circuit breaker!\n"
                        f"{would_restrict} из {len(active_subs)} пользователей превышают лимит.\n"
                        f"Проверьте данные статистики.",
                    )
            except Exception as e:
                logger.error(f"[YandexQuota] Failed to notify admin: {e}")
            return

    warn_threshold = int(limit_bytes * 0.8)

    for sub in active_subs:
        user_traffic = traffic.get(str(sub.user_remna_id), 0)
        tid = sub.user_telegram_id

        quota = await quota_dao.get_by_telegram_id(tid)
        if quota is None:
            quota = UserYandexQuotaDto(
                user_telegram_id=tid,
                period_start=_month_start(now),
            )

        effective_traffic = max(0, user_traffic - quota.reset_baseline_bytes)
        quota.used_bytes = effective_traffic
        quota.last_checked_at = now

        used_gb = effective_traffic / 1024**3
        limit_gb = yandex.monthly_limit_gb

        # Warning at 80%
        if effective_traffic >= warn_threshold and quota.warned_at is None:
            logger.info(
                f"[YandexQuota] {'[DRY-RUN] Would warn' if dry_run else 'Warning'} "
                f"user {tid} ({used_gb:.1f} GB / {limit_gb} GB)"
            )
            if not dry_run:
                try:
                    await bot.send_message(
                        tid,
                        i18n.get(
                            "ntf-yandex.warn",
                            used_gb=f"{used_gb:.1f}",
                            limit_gb=str(limit_gb),
                        ),
                        parse_mode=ParseMode.HTML,
                    )
                except Exception as e:
                    logger.warning(f"[YandexQuota] Could not warn user {tid}: {e}")
                quota.warned_at = now  # only mark as warned after real notification

        # Block at 100%
        if effective_traffic > limit_bytes and not quota.is_restricted:
            logger.info(
                f"[YandexQuota] {'[DRY-RUN] Would restrict' if dry_run else 'Restricting'} "
                f"user {tid} ({used_gb:.1f} GB / {limit_gb} GB)"
            )
            if not dry_run:
                try:
                    await remnawave.update_user_squads(
                        sub.user_remna_id,
                        remove_squad=squad_uuid,
                    )
                    await bot.send_message(
                        tid,
                        i18n.get(
                            "ntf-yandex.limited",
                            limit_gb=str(limit_gb),
                            reset_price=str(yandex.reset_price_rub),
                        ),
                        parse_mode=ParseMode.HTML,
                    )
                    quota.is_restricted = True
                    quota.restricted_at = now
                except Exception as e:
                    logger.error(f"[YandexQuota] Failed to restrict user {tid}: {e}")
                    continue  # Skip saving quota if restriction failed

        await quota_dao.upsert(quota)

    await uow.commit()
    logger.info(
        f"[YandexQuota] Check complete. Active: {len(active_subs)}, "
        f"Over quota: {would_restrict}{'  [DRY-RUN]' if dry_run else ''}"
    )


@broker.task(schedule=[{"cron": "0 0 1 * *"}], retry_on_error=False)
@inject(patch_module=True)
async def reset_yandex_monthly(
    config: FromDishka[AppConfig],
    remnawave: FromDishka[Remnawave],
    subscription_dao: FromDishka[SubscriptionDao],
    quota_dao: FromDishka[YandexQuotaDao],
    uow: FromDishka[UnitOfWork],
    bot: FromDishka[Bot],
    i18n: FromDishka[TranslatorRunner],
) -> None:
    yandex = config.yandex

    if not yandex.enabled:
        logger.debug("[YandexQuota] Monthly reset: feature disabled")
        return

    squad_uuid = UUID(yandex.squad_uuid)  # type: ignore[arg-type]
    dry_run = yandex.dry_run
    now = datetime.now(timezone.utc)
    new_period_start = _month_start(now)

    if dry_run:
        logger.info("[YandexQuota] Monthly reset: DRY-RUN mode enabled")

    restricted = await quota_dao.get_all_restricted()
    logger.info(f"[YandexQuota] Monthly reset: {len(restricted)} restricted users to restore")

    monthly_reset_text = i18n.get("ntf-yandex.monthly-reset")

    for quota in restricted:
        tid = quota.user_telegram_id
        sub = await subscription_dao.get_by_telegram_id(tid)

        if sub and sub.user_remna_id:
            logger.info(
                f"[YandexQuota] {'[DRY-RUN] Would restore' if dry_run else 'Restoring'} "
                f"Yandex access for user {tid}"
            )
            if not dry_run:
                try:
                    await remnawave.update_user_squads(
                        sub.user_remna_id,
                        add_squad=squad_uuid,
                    )
                    await bot.send_message(tid, monthly_reset_text, parse_mode=ParseMode.HTML)
                except Exception as e:
                    logger.error(f"[YandexQuota] Failed to restore user {tid}: {e}")
                    continue

        quota.is_restricted = False
        quota.used_bytes = 0
        quota.reset_baseline_bytes = 0
        quota.period_start = new_period_start
        quota.warned_at = None
        quota.restricted_at = None
        await quota_dao.upsert(quota)

    # Clear warned_at and baseline for warned (but not restricted) users + notify them
    all_quotas = await quota_dao.get_all()
    warned_non_restricted = [q for q in all_quotas if not q.is_restricted and q.warned_at is not None]
    for quota in warned_non_restricted:
        tid = quota.user_telegram_id
        if not dry_run:
            try:
                await bot.send_message(tid, monthly_reset_text, parse_mode=ParseMode.HTML)
            except Exception as e:
                logger.warning(f"[YandexQuota] Could not notify warned user {tid}: {e}")
        quota.warned_at = None
        quota.reset_baseline_bytes = 0
        quota.period_start = new_period_start
        await quota_dao.upsert(quota)
    if warned_non_restricted:
        logger.info(
            f"[YandexQuota] Monthly reset: cleared warnings and notified "
            f"{len(warned_non_restricted)} non-restricted users"
        )

    await uow.commit()
    logger.info("[YandexQuota] Monthly reset complete")
