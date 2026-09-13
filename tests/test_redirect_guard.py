"""
Кому бот открывает экраны в телеграме.

У зарегистрированных на сайте телеграмного чата нет: сайт присылает им
псевдо-id вида -user.id. Попытка открыть им экран заканчивалась ответом
'chat not found' на каждой оплате с сайта.
"""

import pytest

from src.infrastructure.services.redirect import _has_telegram_chat


@pytest.mark.parametrize("telegram_id", [1075319630, 1, 744170701])
def test_real_telegram_user_gets_the_screen(telegram_id: int) -> None:
    assert _has_telegram_chat(telegram_id) is True


@pytest.mark.parametrize("telegram_id", [-31, -1, -54, 0, None])
def test_web_only_user_is_skipped(telegram_id: int | None) -> None:
    # Ноль и None сюда же: чата с таким номером тоже не существует.
    assert _has_telegram_chat(telegram_id) is False
