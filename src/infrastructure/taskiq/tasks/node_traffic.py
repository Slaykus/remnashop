"""
Node traffic quota enforcement.

Architecture:
- Hourly: check per-user traffic on monitored nodes via BandwidthStats API
  - Warn at 80% -> send Telegram notification
  - Block at 100% -> remove node squad from user's active_internal_squads
  - Circuit breaker: abort if >CIRCUIT_BREAKER_PCT% users would be restricted
- Monthly (1st of month 00:00): reset quota, restore squad access for restricted users

Safety:
- NODE_QUOTA_DRY_RUN=true by default - logs what would happen but makes no changes
- Feature disabled entirely when NODE_QUOTA_SQUAD_UUID is not set
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
from src.application.common.dao.node_quota import NodeQuotaDao
from src.application.common.uow import UnitOfWork
from src.application.dto.node_quota import UserNodeQuotaDto
from src.core.config import AppConfig
from src.infrastructure.taskiq.broker import broker

NODE_QUOTA_LOCK_KEY = "node_quota:task_lock"


def _month_start(dt: datetime) -> datetime:
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def _acquire_node_quota_lock(
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
            name=NODE_QUOTA_LOCK_KEY,
            value=token,
            ex=ttl_seconds,
            nx=True,
        )
        if acquired:
            logger.debug(
                f"[NodeQuota] Acquired task lock '{NODE_QUOTA_LOCK_KEY}' for '{owner}'"
            )
            return token

        if asyncio.get_running_loop().time() >= deadline:
            logger.warning(
                f"[NodeQuota] Task '{owner}' skipped: another node quota task is running"
            )
            return None

        await asyncio.sleep(1)


async def _release_node_quota_lock(redis: Redis, token: str) -> None:
    script = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    end
    return 0
    """
    try:
        await redis.eval(script, 1, NODE_QUOTA_LOCK_KEY, token)
        logger.debug(f"[NodeQuota] Released task lock '{NODE_QUOTA_LOCK_KEY}'")
    except Exception as e:
        logger.error(f"[NodeQuota] Failed to release task lock: {e}")


@broker.task(schedule=[{"cron": "5 * * * *"}], retry_on_error=False)
@inject(patch_module=True)
async def check_node_traffic(
    config: FromDishka[AppConfig],
    sdk: FromDishka[RemnawaveSDK],
    remnawave: FromDishka[Remnawave],
    subscription_dao: FromDishka[SubscriptionDao],
    quota_dao: FromDishka[NodeQuotaDao],
    uow: FromDishka[UnitOfWork],
    bot: FromDishka[Bot],
    i18n: FromDishka[TranslatorRunner],
    redis: FromDishka[Redis],
) -> None:
    token = await _acquire_node_quota_lock(
        redis,
        owner="check_node_traffic",
        ttl_seconds=55 * 60,
        wait_seconds=0,
    )
    if token is None:
        return

    try:
        await _check_node_traffic(
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
        await _release_node_quota_lock(redis, token)


async def _check_node_traffic(
    config: AppConfig,
    sdk: RemnawaveSDK,
    remnawave: Remnawave,
    subscription_dao: SubscriptionDao,
    quota_dao: NodeQuotaDao,
    uow: UnitOfWork,
    bot: Bot,
    i18n: TranslatorRunner,
) -> None:
    node_quota = config.node_quota

    if not node_quota.enabled:
        logger.debug("[NodeQuota] Feature disabled (NODE_QUOTA_SQUAD_UUID not set)")
        return

    now = datetime.now(timezone.utc)
    limit_bytes = node_quota.monthly_limit_gb * 1024**3
    squad_uuid = UUID(node_quota.squad_uuid)  # type: ignore[arg-type]
    dry_run = node_quota.dry_run

    if dry_run:
        logger.info("[NodeQuota] DRY-RUN mode enabled - no changes will be made")

    current_period_start = _month_start(now)
    all_quotas = await quota_dao.get_all()
    stale_period_count = sum(1 for quota in all_quotas if quota.period_start < current_period_start)
    if stale_period_count:
        logger.warning(
            f"[NodeQuota] Found {stale_period_count} stale quota records before hourly "
            "check; running monthly reset catch-up"
        )
        await _reset_node_monthly(
            config=config,
            remnawave=remnawave,
            subscription_dao=subscription_dao,
            quota_dao=quota_dao,
            uow=uow,
        )

    traffic: dict[str, int] = defaultdict(int)
    month_start_iso = current_period_start.isoformat()
    now_iso = now.isoformat()

    for node_uuid_str in node_quota.node_uuid_list:
        try:
            result = await sdk.bandwidthstats.get_node_users_usage_legacy_stats(
                uuid=node_uuid_str,
                start=month_start_iso,
                end=now_iso,
            )
            for item in result.response:
                traffic[str(item.user_uuid)] += item.total
            logger.info(
                f"[NodeQuota] Node {node_uuid_str}: got stats for {len(result.response)} users, "
                f"total traffic: {sum(i.total for i in result.response) / 1024**3:.2f} GB"
            )
        except Exception as e:
            logger.error(f"[NodeQuota] Failed to get stats for node {node_uuid_str}: {e}")
            return

    active_subs = await subscription_dao.get_all_active()
    active_subs = sorted(active_subs, key=lambda sub: sub.user_telegram_id or 0)

    if not active_subs:
        logger.debug("[NodeQuota] No active subscriptions, nothing to check")
        return

    would_restrict = sum(
        1 for sub in active_subs if traffic.get(str(sub.user_remna_id), 0) > limit_bytes
    )
    if would_restrict > 0:
        pct = would_restrict / len(active_subs) * 100
        if pct > node_quota.circuit_breaker_pct:
            logger.error(
                f"[NodeQuota] Circuit breaker: {would_restrict}/{len(active_subs)} "
                f"users ({pct:.1f}%) exceed quota. Aborting."
            )
            try:
                owner_id = config.bot.owner_id
                if owner_id:
                    await bot.send_message(
                        owner_id,
                        "⚠️ <b>Сработал circuit breaker для квоты трафика нод</b>\n\n"
                        f"{would_restrict} из {len(active_subs)} активных пользователей "
                        "превышают лимит. Проверьте статистику трафика перед "
                        "продолжением ограничений.",
                        parse_mode=ParseMode.HTML,
                    )
            except Exception as e:
                logger.error(f"[NodeQuota] Failed to notify admin: {e}")
            return

    warn_threshold = int(limit_bytes * 0.8)

    for sub in active_subs:
        user_traffic = traffic.get(str(sub.user_remna_id), 0)
        tid = sub.user_telegram_id

        quota = await quota_dao.get_by_telegram_id(tid)
        if quota is None:
            quota = UserNodeQuotaDto(
                user_telegram_id=tid,
                period_start=_month_start(now),
            )

        effective_traffic = max(0, user_traffic - quota.reset_baseline_bytes)
        quota.used_bytes = effective_traffic
        quota.last_checked_at = now

        used_gb = effective_traffic / 1024**3
        limit_gb = node_quota.monthly_limit_gb

        if effective_traffic >= warn_threshold and quota.warned_at is None:
            logger.info(
                f"[NodeQuota] {'[DRY-RUN] Would warn' if dry_run else 'Warning'} "
                f"user {tid} ({used_gb:.1f} GB / {limit_gb} GB)"
            )
            if not dry_run:
                try:
                    await bot.send_message(
                        tid,
                        i18n.get(
                            "ntf-node-quota.warn",
                            used_gb=f"{used_gb:.1f}",
                            limit_gb=str(limit_gb),
                        ),
                        parse_mode=ParseMode.HTML,
                    )
                except Exception as e:
                    logger.warning(f"[NodeQuota] Could not warn user {tid}: {e}")
                else:
                    quota.warned_at = now

        if effective_traffic > limit_bytes and not quota.is_restricted:
            logger.info(
                f"[NodeQuota] {'[DRY-RUN] Would restrict' if dry_run else 'Restricting'} "
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
                            "ntf-node-quota.limited",
                            limit_gb=str(limit_gb),
                            reset_price=str(node_quota.reset_price_rub),
                        ),
                        parse_mode=ParseMode.HTML,
                    )
                    quota.is_restricted = True
                    quota.restricted_at = now
                except Exception as e:
                    logger.error(f"[NodeQuota] Failed to restrict user {tid}: {e}")
                    continue

        if not dry_run:
            await quota_dao.upsert(quota)

    if not dry_run:
        await uow.commit()
    logger.info(
        f"[NodeQuota] Check complete. Active: {len(active_subs)}, "
        f"Over quota: {would_restrict}{'  [DRY-RUN]' if dry_run else ''}"
    )


@broker.task(schedule=[{"cron": "0 0 1 * *"}], retry_on_error=False)
@inject(patch_module=True)
async def reset_node_monthly(
    config: FromDishka[AppConfig],
    remnawave: FromDishka[Remnawave],
    subscription_dao: FromDishka[SubscriptionDao],
    quota_dao: FromDishka[NodeQuotaDao],
    uow: FromDishka[UnitOfWork],
    redis: FromDishka[Redis],
) -> None:
    token = await _acquire_node_quota_lock(
        redis,
        owner="reset_node_monthly",
        ttl_seconds=2 * 60 * 60,
        wait_seconds=5 * 60,
    )
    if token is None:
        logger.error("[NodeQuota] Monthly reset could not acquire lock")
        return

    try:
        await _reset_node_monthly(
            config=config,
            remnawave=remnawave,
            subscription_dao=subscription_dao,
            quota_dao=quota_dao,
            uow=uow,
        )
    finally:
        await _release_node_quota_lock(redis, token)


@broker.task(retry_on_error=False)
@inject(patch_module=True)
async def restore_node_squad_for_active_users(
    config: FromDishka[AppConfig],
    remnawave: FromDishka[Remnawave],
    subscription_dao: FromDishka[SubscriptionDao],
    redis: FromDishka[Redis],
) -> None:
    token = await _acquire_node_quota_lock(
        redis,
        owner="restore_node_squad_for_active_users",
        ttl_seconds=2 * 60 * 60,
        wait_seconds=0,
    )
    if token is None:
        return

    try:
        await _restore_node_squad_for_active_users(
            config=config,
            remnawave=remnawave,
            subscription_dao=subscription_dao,
        )
    finally:
        await _release_node_quota_lock(redis, token)


async def _reset_node_monthly(
    config: AppConfig,
    remnawave: Remnawave,
    subscription_dao: SubscriptionDao,
    quota_dao: NodeQuotaDao,
    uow: UnitOfWork,
) -> None:
    node_quota = config.node_quota

    if not node_quota.enabled:
        logger.debug("[NodeQuota] Monthly reset: feature disabled")
        return

    squad_uuid = UUID(node_quota.squad_uuid)  # type: ignore[arg-type]
    dry_run = node_quota.dry_run
    now = datetime.now(timezone.utc)
    new_period_start = _month_start(now)

    if dry_run:
        logger.info("[NodeQuota] Monthly reset: DRY-RUN mode enabled")

    all_quotas = await quota_dao.get_all()
    restricted = [quota for quota in all_quotas if quota.is_restricted]
    logger.info(
        f"[NodeQuota] Monthly reset: {len(all_quotas)} quota records, "
        f"{len(restricted)} restricted users to restore"
    )

    # Close the read-only transaction before slow external API and Telegram calls.
    await uow.commit()

    keep_restricted_ids: list[int] = []

    for quota in restricted:
        tid = quota.user_telegram_id
        sub = await subscription_dao.get_current_by_telegram_id(tid)

        if not sub or not sub.user_remna_id:
            logger.warning(
                f"[NodeQuota] No current subscription for restricted user {tid}; "
                "quota will be reset locally"
            )
            continue

        logger.info(
            f"[NodeQuota] {'[DRY-RUN] Would restore' if dry_run else 'Restoring'} "
            f"node squad access for user {tid}"
        )

        if dry_run:
            continue

        try:
            await remnawave.update_user_squads(sub.user_remna_id, add_squad=squad_uuid)
        except Exception as e:
            logger.error(f"[NodeQuota] Failed to restore user {tid}: {e}")
            keep_restricted_ids.append(tid)

    if dry_run:
        logger.info("[NodeQuota] Monthly reset dry-run complete; no records were changed")
        return

    reset_count = await quota_dao.reset_monthly(
        period_start=new_period_start,
        keep_restricted_ids=keep_restricted_ids,
    )
    await uow.commit()

    logger.info(
        f"[NodeQuota] Monthly reset complete. Reset records: {reset_count}, "
        f"kept restricted: {len(keep_restricted_ids)}"
    )


async def _restore_node_squad_for_active_users(
    config: AppConfig,
    remnawave: Remnawave,
    subscription_dao: SubscriptionDao,
) -> None:
    node_quota = config.node_quota

    if not node_quota.enabled:
        logger.warning("[NodeQuota] Cannot restore node squad: feature disabled")
        return

    squad_uuid = UUID(node_quota.squad_uuid)  # type: ignore[arg-type]
    active_subs = await subscription_dao.get_all_active()
    active_subs = sorted(active_subs, key=lambda sub: sub.user_telegram_id or 0)

    restored = 0
    skipped = 0
    failed = 0

    logger.info(
        f"[NodeQuota] Restoring node squad '{squad_uuid}' for "
        f"{len(active_subs)} active users"
    )

    for sub in active_subs:
        if not sub.user_remna_id:
            skipped += 1
            logger.warning(
                f"[NodeQuota] Skipping user {sub.user_telegram_id}: missing Remnawave UUID"
            )
            continue

        if node_quota.dry_run:
            restored += 1
            logger.info(
                f"[NodeQuota] [DRY-RUN] Would restore node squad for user "
                f"{sub.user_telegram_id}"
            )
            continue

        try:
            await remnawave.update_user_squads(sub.user_remna_id, add_squad=squad_uuid)
            restored += 1
        except Exception as e:
            failed += 1
            logger.error(
                f"[NodeQuota] Failed to restore node squad for user "
                f"{sub.user_telegram_id}: {e}"
            )

    logger.info(
        f"[NodeQuota] Node squad restore complete. Restored: {restored}, "
        f"skipped: {skipped}, failed: {failed}"
    )
