"""
Backfill script: paid_referrals_count + milestone discounts for existing users.

For each user who has referred at least one person who made a first payment
(purchase_type=NEW, status=COMPLETED), this script:
  1. Counts how many such "active referrals" they have
  2. Sets paid_referrals_count to that value
  3. Applies the milestone discount: max(current_personal_discount, milestone_discount)
     — so no admin-set discount is ever lowered

Tier table:
  1–2  active referrals → 💧 Капля  → 5%
  3–4  active referrals → ☁️ Облако → 10%
  5–9  active referrals → ⛈️ Шторм  → 15%
  10+  active referrals → 🌧️ Дождь  → 25%

Run inside the Docker container:
    docker compose exec remnashop python scripts/backfill_referral_milestones.py

Or with --dry-run to preview changes without writing to DB:
    docker compose exec remnashop python scripts/backfill_referral_milestones.py --dry-run
"""

import asyncio
import os
import sys

sys.path.insert(0, "/opt/remnashop")


def get_milestone_discount(count: int) -> int:
    if count >= 10:
        return 25
    if count >= 5:
        return 15
    if count >= 3:
        return 10
    if count >= 1:
        return 5
    return 0


def get_tier_label(count: int) -> str:
    if count >= 10:
        return "🌧️ Дождь (4)"
    if count >= 5:
        return "⛈️ Шторм (3)"
    if count >= 3:
        return "☁️ Облако (2)"
    if count >= 1:
        return "💧 Капля (1)"
    return "— (0)"


async def main(dry_run: bool) -> None:
    import sqlalchemy as sa
    from sqlalchemy.ext.asyncio import create_async_engine

    # Build DSN from individual DATABASE_* env vars (how the app configures the DB)
    host = os.environ.get("DATABASE_HOST", "remnashop-db")
    port = os.environ.get("DATABASE_PORT", "5432")
    name = os.environ.get("DATABASE_NAME", "remnashop")
    user = os.environ.get("DATABASE_USER", "remnashop")
    password = os.environ.get("DATABASE_PASSWORD", "")

    if not password:
        print("ERROR: DATABASE_PASSWORD env var is not set.")
        sys.exit(1)

    db_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"

    engine = create_async_engine(db_url, echo=False)

    # Query: for each referrer, count distinct referred users who have ≥1 NEW COMPLETED tx
    count_query = sa.text("""
        SELECT
            r.referrer_telegram_id,
            COUNT(DISTINCT r.referred_telegram_id) AS paid_count
        FROM referrals r
        WHERE r.level = 'FIRST'
          AND EXISTS (
              SELECT 1 FROM transactions t
              WHERE t.user_telegram_id = r.referred_telegram_id
                AND t.purchase_type = 'NEW'
                AND t.status = 'COMPLETED'
          )
        GROUP BY r.referrer_telegram_id
        ORDER BY paid_count DESC
    """)

    current_discounts_query = sa.text("""
        SELECT telegram_id, personal_discount, paid_referrals_count
        FROM users
        WHERE telegram_id = ANY(:ids)
    """)

    update_query = sa.text("""
        UPDATE users
        SET paid_referrals_count = :new_count,
            personal_discount    = GREATEST(personal_discount, :milestone_discount)
        WHERE telegram_id = :telegram_id
    """)

    async with engine.begin() as conn:
        result = await conn.execute(count_query)
        rows = result.fetchall()

    if not rows:
        print("No referrers with active referrals found. Nothing to update.")
        await engine.dispose()
        return

    referrer_ids = [row[0] for row in rows]
    counts = {row[0]: row[1] for row in rows}

    async with engine.begin() as conn:
        disc_result = await conn.execute(
            current_discounts_query, {"ids": referrer_ids}
        )
        current_data = {row[0]: (row[1], row[2]) for row in disc_result.fetchall()}

    print(f"\n{'DRY RUN — no changes written' if dry_run else 'LIVE RUN — writing to DB'}")
    print(f"{'=' * 60}")
    print(f"{'telegram_id':<15} {'paid_count':>10} {'tier':<20} {'old_disc':>8} {'new_disc':>8} {'was_updated':>4}")
    print(f"{'-' * 70}")

    updates = []
    for telegram_id in referrer_ids:
        paid_count = counts[telegram_id]
        milestone_discount = get_milestone_discount(paid_count)
        old_discount, old_count = current_data.get(telegram_id, (0, 0))
        new_discount = max(old_discount, milestone_discount)
        will_update = paid_count != old_count or new_discount != old_discount
        tier = get_tier_label(paid_count)
        print(
            f"{telegram_id:<15} {paid_count:>10} {tier:<20} "
            f"{old_discount:>7}% {new_discount:>7}% {'YES' if will_update else 'no':>7}"
        )
        if will_update:
            updates.append((telegram_id, paid_count, milestone_discount))

    print(f"\nTotal referrers found: {len(rows)}")
    print(f"Referrers to update:   {len(updates)}")

    if not updates:
        print("\nAll referrers already up to date. Nothing to write.")
        await engine.dispose()
        return

    if dry_run:
        print("\n[DRY RUN] No changes written. Run without --dry-run to apply.")
    else:
        async with engine.begin() as conn:
            for telegram_id, new_count, milestone_discount in updates:
                await conn.execute(
                    update_query,
                    {
                        "telegram_id": telegram_id,
                        "new_count": new_count,
                        "milestone_discount": milestone_discount,
                    },
                )
        print(f"\n✅ Updated {len(updates)} referrers successfully.")

    await engine.dispose()


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    asyncio.run(main(dry_run))
