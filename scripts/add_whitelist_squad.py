#!/usr/bin/env python3
"""
Add Whitelist-servers squad to all users who don't have the Free squad.

Usage:
    # Dry run (default) — shows what would happen, makes no changes:
    python scripts/add_whitelist_squad.py

    # Actually apply:
    python scripts/add_whitelist_squad.py --apply

Requires: httpx  (already in project venv)
    uv run python scripts/add_whitelist_squad.py [--apply]
"""

import asyncio
import io
import sys
from uuid import UUID

# Force UTF-8 output on Windows to avoid UnicodeEncodeError with emoji
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import httpx

# ── Config ────────────────────────────────────────────────────────────────────
REMNAWAVE_HOST  = "raincontrol.rainvpn.ru"
REMNAWAVE_TOKEN = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
    ".eyJ1dWlkIjoiYjg3MzMzNzMtZjhhMy00ZTM5LWIyZDgtYjMzZDc2NDIwOTNkIiwidXNlcm5hbWUiOm51bGwsInJvbGUiOiJBUEkiLCJpYXQiOjE3NjYxNzM3OTUsImV4cCI6MTA0MDYwODczOTV9"
    ".rLG8NpjD3102ATte4-Zkj8NqsJHdUPPxfYya-_SV9pI"
)

WHITELIST_SQUAD_UUID = UUID("3d8c6c83-0c04-479e-a478-90636d057944")  # Whitelist-servers
FREE_SQUAD_NAME      = "Free"   # Name to look up (case-insensitive)

PAGE_SIZE = 500   # users per request
# ─────────────────────────────────────────────────────────────────────────────

DRY_RUN = "--apply" not in sys.argv

BASE_URL = f"https://{REMNAWAVE_HOST}/api"
HEADERS  = {
    "Authorization": f"Bearer {REMNAWAVE_TOKEN}",
    "Content-Type":  "application/json",
}


async def main() -> None:
    print(f"{'[DRY-RUN] No changes will be made.' if DRY_RUN else '[APPLY MODE] Changes WILL be applied.'}")
    print(f"Target: {BASE_URL}\n")

    async with httpx.AsyncClient(headers=HEADERS, timeout=60, verify=True) as client:

        # ── 1. Find Free squad UUID ──────────────────────────────────────────
        r = await client.get(f"{BASE_URL}/internal-squads")
        r.raise_for_status()
        data = r.json()

        # Normalize: API wraps responses in {"response": {...}}
        if isinstance(data, dict) and "response" in data:
            data = data["response"]
        if isinstance(data, list):
            squads_raw = data
        elif isinstance(data, dict):
            squads_raw = data.get("internalSquads") or data.get("squads") or []
        else:
            print(f"Unexpected response: {data}")
            return

        free_squad_uuid: UUID | None = None
        print("Available squads:")
        for sq in squads_raw:
            if not isinstance(sq, dict):
                print(f"  (unexpected item format: {sq!r})")
                continue
            sq_uuid = sq.get("uuid", "?")
            sq_name = sq.get("name", "?")
            print(f"  {sq_uuid}  {sq_name}")
            if sq_name.lower() == FREE_SQUAD_NAME.lower():
                free_squad_uuid = UUID(sq_uuid)

        if free_squad_uuid is None:
            print(f"\n❌ Squad '{FREE_SQUAD_NAME}' not found! Check the name above.")
            return

        print(f"\n✅ Free squad:            {free_squad_uuid}")
        print(f"✅ Whitelist-servers squad: {WHITELIST_SQUAD_UUID}\n")

        # ── 2. Fetch all users (paginated) ───────────────────────────────────
        all_users = []
        start = 0
        while True:
            r = await client.get(
                f"{BASE_URL}/users",
                params={"start": start, "size": PAGE_SIZE},
            )
            r.raise_for_status()
            body = r.json()
            if isinstance(body, dict) and "response" in body:
                body = body["response"]
            batch = body.get("users", [])
            all_users.extend(batch)
            total = body.get("total", 0)
            print(f"  Fetched {len(all_users)}/{total} users...")
            if len(all_users) >= total or not batch:
                break
            start += PAGE_SIZE

        print(f"\nTotal users fetched: {len(all_users)}")

        # ── 3. Filter ────────────────────────────────────────────────────────
        # Build map: user_uuid → current squad UUIDs (needed for individual PATCH)
        to_add: list[tuple[UUID, list[UUID]]] = []  # (user_uuid, current_squads)
        skipped_free = 0
        already_has  = 0

        for user in all_users:
            user_uuid = UUID(user["uuid"])
            active_squads = [
                UUID(s["uuid"])
                for s in (user.get("activeInternalSquads") or [])
            ]

            if free_squad_uuid in active_squads:
                skipped_free += 1
                continue

            if WHITELIST_SQUAD_UUID in active_squads:
                already_has += 1
                continue

            to_add.append((user_uuid, active_squads))

        print(f"\nResults of filtering:")
        print(f"  Will add Whitelist-servers:   {len(to_add)}")
        print(f"  Skipped (have Free squad):     {skipped_free}")
        print(f"  Skipped (already Whitelist):   {already_has}")

        if not to_add:
            print("\nNothing to do.")
            return

        if DRY_RUN:
            print(f"\n[DRY-RUN] Would add {len(to_add)} users to Whitelist-servers.")
            print("Run with --apply to execute.")
            return

        # ── 4. Add individually via PATCH /users ──────────────────────────────
        # NOTE: bulk-add endpoint adds ALL users regardless of the userUuids payload,
        # so we patch each user individually with their updated squad list.
        print(f"\nAdding Whitelist-servers to {len(to_add)} users individually...")
        ok = 0
        errors = 0
        for i, (user_uuid, current_squads) in enumerate(to_add, 1):
            new_squads = current_squads + [WHITELIST_SQUAD_UUID]
            r = await client.patch(
                f"{BASE_URL}/users",
                json={
                    "uuid": str(user_uuid),
                    "activeInternalSquads": [str(s) for s in new_squads],
                },
            )
            if r.is_success:
                ok += 1
            else:
                print(f"  [ERROR] {user_uuid}: {r.status_code} {r.text[:120]}")
                errors += 1
            if i % 20 == 0:
                print(f"  Progress: {i}/{len(to_add)} ({ok} ok, {errors} errors)")

        print(f"\n✅ Done! {ok} users updated, {errors} errors.")


if __name__ == "__main__":
    asyncio.run(main())
