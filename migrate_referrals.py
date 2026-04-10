"""
One-time migration: SQLite referrals → PostgreSQL (remnashop)

Generates a SQL file, then run it via docker exec:
    python migrate_referrals.py
    docker exec -i remnashop-db psql -U remnashop -d remnashop < referrals_migration.sql
"""

import sqlite3
from datetime import datetime, timezone


SQLITE_PATH = "bot_database.sqlite3"
OUTPUT_SQL = "referrals_migration.sql"


def parse_dt(s):
    if not s:
        return datetime.now(timezone.utc).isoformat()
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def q(s):
    """Escape single quotes for SQL."""
    return str(s).replace("'", "''")


def main():
    con = sqlite3.connect(SQLITE_PATH)
    cur = con.cursor()
    cur.execute("SELECT referred_tg_id, referrer_tg_id, created_at FROM referrals ORDER BY id")
    referrals = cur.fetchall()
    cur.execute(
        "SELECT user_tg_id, amount, created_at, rewarded_at FROM referrer_rewards ORDER BY id"
    )
    rewards = cur.fetchall()
    con.close()

    print(f"SQLite: {len(referrals)} referrals, {len(rewards)} rewards")

    lines = []
    lines.append("BEGIN;\n")

    # ── Step 1: referrals ─────────────────────────────────────────────────────
    lines.append("-- Step 1: referrals")
    lines.append("-- Skips rows where either user doesn't exist (FK check) or duplicate referred_telegram_id")
    for referred_tg_id, referrer_tg_id, created_at in referrals:
        dt = q(parse_dt(created_at))
        lines.append(
            f"INSERT INTO referrals (referrer_telegram_id, referred_telegram_id, level, created_at, updated_at)"
            f" SELECT {referrer_tg_id}, {referred_tg_id}, 'FIRST', '{dt}', '{dt}'"
            f" WHERE EXISTS (SELECT 1 FROM users WHERE telegram_id = {referrer_tg_id})"
            f" AND EXISTS (SELECT 1 FROM users WHERE telegram_id = {referred_tg_id})"
            f" ON CONFLICT (referred_telegram_id) DO NOTHING;"
        )

    lines.append("")

    # ── Step 2: referral_rewards ──────────────────────────────────────────────
    lines.append("-- Step 2: referral_rewards (linked to earliest matching referral)")
    lines.append("-- All marked is_issued=true so no new rewards will fire")
    lines.append("DO $$")
    lines.append("DECLARE v_referral_id INTEGER;")
    lines.append("BEGIN")
    for user_tg_id, amount, created_at, rewarded_at in rewards:
        is_issued = "true" if rewarded_at else "false"
        dt = q(parse_dt(created_at))
        amount_int = int(float(amount))
        lines.append(
            f"  SELECT id INTO v_referral_id FROM referrals"
            f" WHERE referrer_telegram_id = {user_tg_id} ORDER BY created_at LIMIT 1;"
        )
        lines.append(
            f"  IF v_referral_id IS NOT NULL THEN"
            f" INSERT INTO referral_rewards"
            f" (referral_id, user_telegram_id, type, amount, is_issued, created_at, updated_at)"
            f" VALUES (v_referral_id, {user_tg_id}, 'EXTRA_DAYS', {amount_int}, {is_issued},"
            f" '{dt}', '{dt}');"
            f" END IF;"
        )
    lines.append("END $$;")
    lines.append("")
    lines.append("COMMIT;")

    sql = "\n".join(lines)

    with open(OUTPUT_SQL, "w") as f:
        f.write(sql)

    print(f"SQL saved to {OUTPUT_SQL}")
    print()
    print("Run on the server:")
    print(f"  docker exec -i remnashop-db psql -U remnashop -d remnashop < {OUTPUT_SQL}")


if __name__ == "__main__":
    main()
