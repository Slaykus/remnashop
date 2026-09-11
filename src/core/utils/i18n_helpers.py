from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, ROUND_UP, Decimal
from typing import Any, Final, Optional, Union

from src.core.constants import UNLIMITED_EXPIRE_YEAR
from src.core.types import I18nValue
from src.core.utils.time import datetime_now

from .i18n_keys import ByteUnitKey, TimeUnitKey, UtilKey


def i18n_format_bytes_to_unit(
    value: Optional[Union[int, float]],
    *,
    round_up: bool = False,
    min_unit: ByteUnitKey = ByteUnitKey.GIGABYTE,
) -> tuple[str, dict[str, float]]:
    if value is None:
        return UtilKey.UNLIMITED, {}

    bytes_value = Decimal(value)
    units: Final[list[ByteUnitKey]] = list(ByteUnitKey)  # [B, KB, MB, GB]

    for i, unit in enumerate(units):
        if i + 1 < len(units):
            next_unit_threshold = Decimal(1024)
            if bytes_value >= next_unit_threshold:
                bytes_value /= Decimal(1024)
            else:
                break

    if units.index(unit) < units.index(min_unit):
        unit = min_unit
        factor = Decimal(1024) ** (units.index(min_unit))
        bytes_value = Decimal(value) / factor

    rounding = ROUND_UP if round_up else ROUND_HALF_UP
    size_formatted = bytes_value.quantize(Decimal("0.01"), rounding=rounding)

    return unit, {"value": float(size_formatted)}


def i18n_format_seconds(
    value: Union[int, float, str],
) -> list[tuple[str, dict[str, int]]]:
    remaining = int(value)
    parts = []

    if remaining < 60:
        return [(TimeUnitKey.MINUTE, {"value": 0})]

    units: dict[str, int] = {
        TimeUnitKey.DAY: 86400,
        TimeUnitKey.HOUR: 3600,
        TimeUnitKey.MINUTE: 60,
    }

    for unit, unit_seconds in units.items():
        value = remaining // unit_seconds
        if value > 0:
            parts.append((unit, {"value": value}))
            remaining %= unit_seconds

    if not parts:
        return [(TimeUnitKey.MINUTE, {"value": 1})]

    return parts


def i18n_format_days(value: int) -> tuple[str, dict[str, int]]:
    if value == 0:
        return UtilKey.UNLIMITED, {}

    if value % 365 == 0:
        return TimeUnitKey.YEAR, {"value": value // 365}

    if value % 30 == 0:
        return TimeUnitKey.MONTH, {"value": value // 30}

    return TimeUnitKey.DAY, {"value": value}


def i18n_format_traffic_limit(value: Optional[int]) -> tuple[str, dict[str, int]]:
    if not value:
        return UtilKey.UNLIMITED, {}

    return ByteUnitKey.GIGABYTE, {"value": value}


def i18n_format_device_limit(value: Optional[int]) -> tuple[str, dict[str, int]]:
    if not value:
        return UtilKey.UNLIMITED, {}

    return UtilKey.UNIT_DEVICE, {"value": value}


def i18n_format_expire_time(expiry: Union[timedelta, datetime]) -> list[tuple[str, dict[str, int]]]:
    # Special case: unlimited remnawave ;D
    if isinstance(expiry, datetime) and expiry.year == UNLIMITED_EXPIRE_YEAR:
        return [(UtilKey.UNLIMITED, {"value": 0})]

    # Convert datetime to timedelta
    if isinstance(expiry, datetime):
        now = datetime_now()
        delta = expiry - now
    else:
        delta = expiry

    if delta.total_seconds() <= 0:
        # Already expired or zero, default to 1 minute
        return [(UtilKey.UNKNOWN, {"value": 0})]

    days = delta.days
    seconds = delta.seconds
    parts: list[tuple[str, dict[str, int]]] = []

    # Years
    years, days = divmod(days, 365)
    if years:
        parts.append((TimeUnitKey.YEAR, {"value": years}))

    # Remaining days
    if days:
        parts.append((TimeUnitKey.DAY, {"value": days}))

    # Hours
    hours, seconds = divmod(seconds, 3600)
    if hours:
        parts.append((TimeUnitKey.HOUR, {"value": hours}))

    # Minutes
    minutes, _ = divmod(seconds, 60)
    if minutes:
        parts.append((TimeUnitKey.MINUTE, {"value": minutes}))

    return parts or [(UtilKey.UNKNOWN, {"value": 0})]


def i18n_plain(value: Union[I18nValue, Any]) -> str:
    """Развернуть i18n-значение в обычный текст.

    Нужно там, где строка уходит наружу мимо переводов — в чек, в платёжку,
    в лог. Пара «ключ + параметры» в таком месте печатается кортежем, и
    человек читает в официальном чеке `('Solo', {})`.

    Тип намеренно шире алиаса: значения приходят из событий, собранных в
    разных местах, и уронить отправку чека из-за неожиданной формы хуже,
    чем напечатать её как есть.
    """
    if isinstance(value, (tuple, list)):
        value = value[0] if value else ""

    if value is None:
        return ""

    return str(value).strip()
