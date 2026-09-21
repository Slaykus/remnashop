"""
Когда на экране устройств предлагать докупку.

Логика отвечает на четыре вопроса сразу: включена ли возможность, есть
ли вообще лимит, не упёрлись ли в потолок докупки и заняты ли слоты. Её
легко собрать неправильно — я и собрал с первого раза, поставив «на
потолке» ветку, которая наоборот показывала подсказку.
"""

import pytest

from src.application.services.device_pricing import MAX_ADDON_DEVICES


def addon_hint(enabled: bool, limit: int, connected: int) -> str:
    """То же, что считает геттер экрана устройств."""
    if not (enabled and limit > 0 and limit + 1 <= MAX_ADDON_DEVICES):
        return "HIDE"
    return "FULL" if connected >= limit else "FREE"


@pytest.mark.parametrize(
    ("enabled", "limit", "connected", "expected"),
    [
        (True, 2, 2, "FULL"),     # слоты заняты — тот, ради кого всё затевалось
        (True, 2, 1, "FREE"),
        (True, 2, 0, "FREE"),
        (True, 4, 4, "FULL"),
        (False, 2, 2, "HIDE"),    # выключено — ни строки, ни кнопки
        (True, 0, 0, "HIDE"),     # безлимит: докупать нечего
        (True, 10, 9, "HIDE"),    # потолок докупки, дальше корпоратив
        (True, 12, 12, "HIDE"),   # выше потолка — тоже молчим
    ],
)
def test_hint_branches(enabled: bool, limit: int, connected: int, expected: str) -> None:
    assert addon_hint(enabled, limit, connected) == expected


def test_disabled_hides_everything_regardless() -> None:
    # Выключатель сильнее любых других условий: он для того и заведён.
    for limit in range(0, MAX_ADDON_DEVICES + 3):
        for connected in range(0, limit + 2):
            assert addon_hint(False, limit, connected) == "HIDE"
