"""
Migration script: bulk-update users in Remnawave panel.

- EXPIRED/DISABLED/LIMITED users → Free squad, hwid_device_limit = 1
- ACTIVE users → double hwid_device_limit, assign to matching squad

Device limit → squad mapping (after doubling):
  1 → Free (already at 1, stays 1 for expired; active with 1 → 2 → Solo)
  2 → Solo
  4 → Duo
  6 → Family
  10 → Team

Run inside the container:
    docker compose exec remnashop python scripts/migrate_users.py
"""

import asyncio
import os
import sys

sys.path.insert(0, "/opt/remnashop")

from httpx import AsyncClient, Timeout
from remnapy import RemnawaveSDK
from remnapy.models import UpdateUserRequestDto

# Device limit after doubling → squad name
LIMIT_TO_SQUAD: dict[int, str] = {
    2: "Solo",
    4: "Duo",
    6: "Family",
    10: "Team",
}

INACTIVE_STATUSES = {"EXPIRED", "DISABLED", "LIMITED"}


def build_sdk() -> RemnawaveSDK:
    host = os.environ.get("REMNAWAVE_HOST", "http://remnawave:3000").strip().rstrip("/")
    if "://" not in host:
        host = f"http://{host}"
    if ":" not in host.split("://")[1]:
        host = f"{host}:3000"

    token = os.environ["REMNAWAVE_TOKEN"]
    caddy_token = os.environ.get("REMNAWAVE_CADDY_TOKEN", "")
    cf_id = os.environ.get("REMNAWAVE_CF_CLIENT_ID", "")
    cf_secret = os.environ.get("REMNAWAVE_CF_CLIENT_SECRET", "")
    cookie = os.environ.get("REMNAWAVE_COOKIE", "")

    headers: dict[str, str] = {"Authorization": f"Bearer {token}"}
    if caddy_token:
        headers["X-Api-Key"] = caddy_token
    if cf_id:
        headers["CF-Access-Client-Id"] = cf_id
    if cf_secret:
        headers["CF-Access-Client-Secret"] = cf_secret

    is_internal = not host.startswith("https://")
    if is_internal:
        headers["x-forwarded-proto"] = "https"
        headers["x-forwarded-for"] = "127.0.0.1"

    from httpx import Cookies
    cookies = Cookies()
    if cookie and "=" in cookie:
        k, v = cookie.split("=", 1)
        cookies.set(k.strip(), v.strip())

    client = AsyncClient(
        base_url=f"{host}/api",
        headers=headers,
        cookies=cookies,
        timeout=Timeout(connect=15.0, read=30.0, write=10.0, pool=5.0),
    )
    return RemnawaveSDK(client)


async def main() -> None:
    sdk = build_sdk()

    # Load squads
    squads_response = await sdk.internal_squads.get_internal_squads()
    squad_map: dict[str, str] = {s.name: str(s.uuid) for s in squads_response.internal_squads}
    print(f"Squads found: {list(squad_map.keys())}")

    free_uuid = squad_map.get("Free")
    if not free_uuid:
        print("ERROR: squad 'Free' not found. Abort.")
        return

    # Load all users
    all_users = []
    limit = 50
    offset = 0
    while True:
        resp = await sdk.users.get_all_users(start=offset, size=limit)
        if not resp.users:
            break
        all_users.extend(resp.users)
        if len(resp.users) < limit:
            break
        offset += len(resp.users)

    print(f"Total users: {len(all_users)}")

    expired_ok = expired_err = 0
    active_ok = active_err = 0

    for user in all_users:
        status = str(user.status).upper() if user.status else ""

        if status in INACTIVE_STATUSES:
            try:
                dto = UpdateUserRequestDto(
                    uuid=user.uuid,
                    username=user.username,
                    hwid_device_limit=1,
                    active_internal_squads=[free_uuid],
                )
                await sdk.users.update_user(dto)
                expired_ok += 1
            except Exception as e:
                print(f"  [EXPIRED] ERROR {user.username}: {e}")
                expired_err += 1

        elif status == "ACTIVE":
            current_limit = user.hwid_device_limit or 1
            new_limit = current_limit * 2
            squad_name = LIMIT_TO_SQUAD.get(new_limit)
            squad_uuid = squad_map.get(squad_name) if squad_name else None

            try:
                dto = UpdateUserRequestDto(
                    uuid=user.uuid,
                    username=user.username,
                    hwid_device_limit=new_limit,
                    active_internal_squads=[squad_uuid] if squad_uuid else None,
                )
                await sdk.users.update_user(dto)
                squad_info = f"→ {squad_name}" if squad_name else "(no squad match)"
                print(f"  [ACTIVE] {user.username}: {current_limit} → {new_limit} {squad_info}")
                active_ok += 1
            except Exception as e:
                print(f"  [ACTIVE] ERROR {user.username}: {e}")
                active_err += 1

    print(
        f"\nDone.\n"
        f"  Expired/Disabled → Free (limit=1): {expired_ok} OK, {expired_err} errors\n"
        f"  Active → doubled limit + squad:     {active_ok} OK, {active_err} errors"
    )


if __name__ == "__main__":
    asyncio.run(main())
