"""
Сверка успешных платежей ЮKassa с таблицей transactions.

Ищет платежи, которые ЮKassa считает проведёнными, а у нас записи о них нет.
Так проявлялось слияние аккаунтов при привязке Telegram: виртуальный аккаунт
удалялся, а каскад уносил его платежи. Деньги клиенты получили, а подтвердить
оплату поддержка могла только банковской справкой.

Только читает — и базу, и ЮKassa. Ключ шлюза расшифровывается тем же
способом, что в CryptographerImpl: Fernet на APP_CRYPT_KEY, префикс enc_.
Приложение целиком не поднимается: сервер мал, а сверке нужны лишь база,
ключ и HTTP.

Запуск внутри контейнера бота:
    docker exec -w /opt/remnashop <cid> .venv/bin/python scripts/reconcile_yookassa.py --since 2026-06-01

Ничего секретного не печатает.
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone

import asyncpg
import httpx
from cryptography.fernet import Fernet

ENCRYPTED_PREFIX = "enc_"  # как в src.core.constants
API = "https://api.yookassa.ru/v3/payments"
PAGE = 100


def _decrypt(value: str, key: str) -> str:
    if not value.startswith(ENCRYPTED_PREFIX):
        return value
    return Fernet(key.encode()).decrypt(value.removeprefix(ENCRYPTED_PREFIX).encode()).decode()


async def _load_database_state() -> tuple[str, str, set[str]]:
    conn = await asyncpg.connect(
        host=os.environ["DATABASE_HOST"],
        port=int(os.environ.get("DATABASE_PORT", "5432")),
        user=os.environ["DATABASE_USER"],
        password=os.environ["DATABASE_PASSWORD"],
        database=os.environ["DATABASE_NAME"],
    )
    try:
        raw = await conn.fetchval("SELECT settings FROM payment_gateways WHERE type = 'YOOKASSA'")
        if raw is None:
            raise SystemExit("YooKassa gateway is not configured")
        settings = json.loads(raw) if isinstance(raw, str) else raw
        shop_id = str(settings["shop_id"])
        api_key = _decrypt(settings["api_key"], os.environ["APP_CRYPT_KEY"])

        rows = await conn.fetch("SELECT payment_id::text AS id FROM transactions")
        return shop_id, api_key, {r["id"] for r in rows}
    finally:
        await conn.close()


async def _succeeded_since(shop_id: str, api_key: str, since: datetime) -> list[dict]:
    params = {
        "status": "succeeded",
        "created_at.gte": since.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "limit": PAGE,
    }
    found: list[dict] = []
    async with httpx.AsyncClient(auth=(shop_id, api_key), timeout=30.0) as client:
        while True:
            r = await client.get(API, params=params)
            r.raise_for_status()
            body = r.json()
            found.extend(body.get("items", []))
            cursor = body.get("next_cursor")
            if not cursor:
                return found
            params = {**params, "cursor": cursor}


def _amount(p: dict) -> str:
    a = p.get("amount", {})
    return f"{a.get('value', '?')} {a.get('currency', '')}".strip()


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--since", default="2026-06-01", help="с какой даты, YYYY-MM-DD (UTC)")
    parser.add_argument("--json", action="store_true", help="вывести недостающие платежи целиком")
    args = parser.parse_args()

    since = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    shop_id, api_key, known = await _load_database_state()
    payments = await _succeeded_since(shop_id, api_key, since)
    missing = [p for p in payments if p["id"] not in known]

    print(f"Успешных платежей в ЮKassa с {args.since}: {len(payments)}")
    print(f"Транзакций в базе бота:                {len(known)}")
    print(f"Платежей без записи в базе:              {len(missing)}")

    for p in sorted(missing, key=lambda x: x.get("created_at", "")):
        line = (
            f"  {p['id']}  {p.get('created_at', '?')}  {_amount(p)}"
            f"  test={p.get('test', False)}  «{p.get('description', '')}»"
        )
        print(line)

    if args.json and missing:
        # Только то, что нужно для восстановления записи. Объект платежа
        # целиком несёт маскированную карту, банк и код авторизации — их
        # хранить незачем.
        trimmed = [
            {
                "id": p["id"],
                "created_at": p.get("created_at"),
                "captured_at": p.get("captured_at"),
                "amount": p.get("amount"),
                "description": p.get("description"),
                "test": p.get("test", False),
            }
            for p in missing
        ]
        print(json.dumps(trimmed, ensure_ascii=False, indent=2))

    # Код возврата удобен для расписания: ненулевой — есть расхождение.
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
