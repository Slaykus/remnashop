"""
Ссылка входа в веб-кабинет.

Виджет Telegram для входа на сайт требует, чтобы у пользователя работал сам
Telegram. Но кабинет и существует ради тех, у кого он недоступен, — значит
опираться на виджет нельзя. Поэтому кнопка «Личный кабинет» ведёт по ссылке
с подписанным токеном: пользователь открывает её, пока связь с ботом ещё
есть, и попадает внутрь уже авторизованным.

Подпись — HMAC на общем секрете APP_WEB_API_KEY, который бот и сайт уже
используют для internal-API. Отдельного секрета заводить не нужно.

Формат токена:  <telegram_id>.<expires_unix>.<hmac_hex>
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from urllib.parse import urlencode

# Токен живёт недолго: он попадает в историю браузера и в буфер обмена,
# а нужен ровно на один переход.
TOKEN_TTL_SECONDS = 300

_ENV_KEY = "APP_WEB_API_KEY"


def _sign(payload: str, secret: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def build_token(telegram_id: int, secret: str, ttl: int = TOKEN_TTL_SECONDS) -> str:
    expires = int(time.time()) + ttl
    payload = f"{telegram_id}.{expires}"
    return f"{payload}.{_sign(payload, secret)}"


def build_cabinet_url(base_url: str, telegram_id: int) -> str:
    """
    Возвращает ссылку на кабинет с токеном входа.

    Если секрет не настроен, отдаёт исходный адрес без токена: кнопка
    продолжит работать, просто пользователю придётся войти вручную.
    """
    base = (base_url or "").strip()
    if not base:
        return ""

    secret = os.environ.get(_ENV_KEY, "")
    if not secret:
        return base

    token = build_token(telegram_id, secret)
    # Путь дописывается к корню сайта, поэтому строка запроса всегда своя.
    root = base.split("?", 1)[0].rstrip("/")
    return f"{root}/auth/tg?{urlencode({'token': token})}"
