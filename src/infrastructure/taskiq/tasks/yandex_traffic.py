"""
Yandex node traffic quota enforcement.

Architecture:
- Hourly: check per-user traffic on Yandex nodes via BandwidthStats API
  - Warn at 80% -> send Telegram notification
  - Block at 100% -> remove Yandex squad from user's active_internal_squads
  - Circuit breaker: abort if >CIRCUIT_BREAKER_PCT% users would be restricted
- Monthly (1st of month 00:00): reset quota, restore squad access for restricted users

Safety:
- YANDEX_DRY_RUN=true by default - logs what would happen but makes no changes
- Feature disabled entirely when YANDEX_SQUAD_UUID is not set
"""

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from aiogram import Bot
from aiogram.enums import ParseMode
from dishka.integrations.taskiq import FromDishka, inject
from loguru import logger
from redis.asyncio import Redis
from remnapy import RemnawaveSDK

from src.application.common import Remnawave, TranslatorRunner
from src.application.common.dao import SubscriptionDao
from src.application.common.dao.yandex_quota import YandexQuotaDao
from src.application.common.uow import UnitOfWork
from src.application.dto.yandex_quota import UserYandexQuotaDto
from src.core.config import AppConfig
from src.infrastructure.taskiq.broker import broker

YANDEX_QUOTA_LOCK_KEY = "yandex_quota:task_lock"


def _month_start(dt: datetime) -> datetime:
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def _acquire_yandex_quota_lock(
    redis: Redis,
    *,
    owner: str,
    ttl_seconds: int,
    wait_seconds: float = 0.0,
) -> Optional[str]:
    token = f"{owner}:{uuid4()}"
    deadline = asyncio.get_running_loop().time() + wait_seconds

    while True:
        acquired = await redis.set(
            name=YANDEX_QUOTA_LOCK_KEY,
            value=token,
            ex=ttl_seconds,
            nx=True,
        )
        if acquired:
            logger.debug(
                f"[YandexQuota] Acquired task lock '{YANDEX_QUOTA_LOCK_KEY}' for '{owner}'"
            )
            return token

        if asyncio.get_running_loop().time() >= deadline:
            logger.warning(
                f"[YandexQuota] Task '{owner}' skipped: another Yandex quota task is running"
            )
            return None

        await asyncio.sleep(1)


async def _release_yandex_quota_lock(redis: Redis, token: str) -> None:
    script = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    end
    return 0
    """
    try:
        await redis.eval(script, 1, YANDEX_QUOTA_LOCK_KEY, token)
        logger.debug(f"[YandexQuota] Released task lock '{YANDEX_QUOTA_LOCK_KEY}'")
    except Exception as e:
        logger.error(f"[YandexQuota] Failed to release task lock: {e}")


@broker.task(schedule=[{"cron": "5 * * * *"}], retry_on_error=False)
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
    redis: FromDishka[Redis],
) -> None:
    token = await _acquire_yandex_quota_lock(
        redis,
        owner="check_yandex_traffic",
        ttl_seconds=55 * 60,
        wait_seconds=0,
    )
    if token is None:
        return

    try:
        await _check_yandex_traffic(
            config=config,
            sdk=sdk,
            remnawave=remnawave,
            subscription_dao=subscription_dao,
            quota_dao=quota_dao,
            uow=uow,
            bot=bot,
            i18n=i18n,
        )
    finally:
        await _release_yandex_quota_lock(redis, token)


async def _check_yandex_traffic(
    config: AppConfig,
    sdk: RemnawaveSDK,
    remnawave: Remnawave,
    subscription_dao: SubscriptionDao,
    quota_dao: YandexQuotaDao,
    uow: UnitOfWork,
    bot: Bot,
    i18n: TranslatorRunner,
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
        logger.info("[YandexQuota] DRY-RUN mode enabled - no changes will be made")

    current_period_start = _month_start(now)
    all_quotas = await quota_dao.get_all()
    stale_period_count = sum(1 for quota in all_quotas if quota.period_start < current_period_start)
    if stale_period_count:
        logger.warning(
            f"[YandexQuota] Found {stale_period_count} stale quota records before hourly "
            "check; running monthly reset catch-up"
        )
        await _reset_yandex_monthly(
            config=config,
            remnawave=remnawave,
            subscription_dao=subscription_dao,
            quota_dao=quota_dao,
            uow=uow,
            bot=bot,
            i18n=i18n,
        )

    traffic: dict[str, int] = defaultdict(int)
    month_start_iso = current_period_start.isoformat()
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
            return

    active_subs = await subscription_dao.get_all_active()
    active_subs = sorted(active_subs, key=lambda sub: sub.user_telegram_id or 0)

    if not active_subs:
        logger.debug("[YandexQuota] No active subscriptions, nothing to check")
        return

    would_restrict = sum(
        1 for sub in active_subs if traffic.get(str(sub.user_remna_id), 0) > limit_bytes
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
                        i18n.get(
                            "ntf-yandex.circuit-breaker",
                            would_restrict=would_restrict,
                            total_users=len(active_subs),
                        ),
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
                else:
                    quota.warned_at = now

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
                    continue

        if not dry_run:
            await quota_dao.upsert(quota)

    if not dry_run:
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
    redis: FromDishka[Redis],
) -> None:
    token = await _acquire_yandex_quota_lock(
        redis,
        owner="reset_yandex_monthly",
        ttl_seconds=2 * 60 * 60,
        wait_seconds=5 * 60,
    )
    if token is None:
        logger.error("[YandexQuota] Monthly reset could not acquire lock")
        return

    try:
        await _reset_yandex_monthly(
            config=config,
            remnawave=remnawave,
            subscription_dao=subscription_dao,
            quota_dao=quota_dao,
            uow=uow,
            bot=bot,
            i18n=i18n,
        )
    finally:
        await _release_yandex_quota_lock(redis, token)


async def _reset_yandex_monthly(
    config: AppConfig,
    remnawave: Remnawave,
    subscription_dao: SubscriptionDao,
    quota_dao: YandexQuotaDao,
    uow: UnitOfWork,
    bot: Bot,
    i18n: TranslatorRunner,
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

    all_quotas = await quota_dao.get_all()
    restricted = [quota for quota in all_quotas if quota.is_restricted]
    warned_non_restricted = [
        quota for quota in all_quotas if not quota.is_restricted and quota.warned_at is not None
    ]
    logger.info(
        f"[YandexQuota] Monthly reset: {len(all_quotas)} quota records, "
        f"{len(restricted)} restricted users to restore"
    )

    # Close the read-only transaction before slow external API and Telegram calls.
    await uow.commit()

    monthly_reset_text = i18n.get("ntf-yandex.monthly-reset")
    keep_restricted_ids: list[int] = []

    for quota in restricted:
        tid = quota.user_telegram_id
        sub = await subscription_dao.get_current(tid)

        if not sub or not sub.user_remna_id:
            logger.warning(
                f"[YandexQuota] No current subscription for restricted user {tid}; "
                "quota will be reset locally"
            )
            continue

        logger.info(
            f"[YandexQuota] {'[DRY-RUN] Would restore' if dry_run else 'Restoring'} "
            f"Yandex access for user {tid}"
        )

        if dry_run:
            continue

        try:
            await remnawave.update_user_squads(sub.user_remna_id, add_squad=squad_uuid)
            await bot.send_message(tid, monthly_reset_text, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.error(f"[YandexQuota] Failed to restore user {tid}: {e}")
            keep_restricted_ids.append(tid)

    for quota in warned_non_restricted:
        tid = quota.user_telegram_id
        if dry_run:
            continue

        try:
            await bot.send_message(tid, monthly_reset_text, parse_mode=ParseMode.HTML)
        except Exception as e:
            logger.warning(f"[YandexQuota] Could not notify warned user {tid}: {e}")

    if dry_run:
        logger.info("[YandexQuota] Monthly reset dry-run complete; no records were changed")
        return

    reset_count = await quota_dao.reset_monthly(
        period_start=new_period_start,
        keep_restricted_ids=keep_restricted_ids,
    )
    await uow.commit()

    logger.info(
        f"[YandexQuota] Monthly reset complete. Reset records: {reset_count}, "
        f"kept restricted: {len(keep_restricted_ids)}"
    )
