"""
Модули должны импортироваться поодиночке.

Цикл между модулями виден не всегда: когда пакет уже загружен чем-то
другим, импорт проходит, и внутри одного прогона тестов всё зелено. Ломается
оно на старте приложения, где порядок импорта другой, — так бот и упал,
когда список сценариев подписки начал тянуть выставление счёта, а оно через
реферальные награды возвращалось в тот же пакет.

Поэтому каждый модуль проверяем в отдельном процессе и первым импортом.
"""

import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent

# Точки входа, с которых начинается загрузка на старте, плюс тот самый
# модуль наград, на котором кольцо и разомкнулось.
ENTRY_POINTS = [
    "src.application.use_cases.referral.commands.rewards",
    "src.application.use_cases.gateways.commands.payment",
    "src.application.use_cases.subscription",
    "src.application.use_cases.subscription.commands.add_device",
    "src.infrastructure.di.providers.use_cases",
    "src.web.endpoints.internal",
]


@pytest.mark.parametrize("module", ENTRY_POINTS)
def test_module_imports_on_its_own(module: str) -> None:
    result = subprocess.run(
        [sys.executable, "-c", f"import {module}"],
        cwd=_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Импорт '{module}' первым не проходит:\n{result.stderr}"
