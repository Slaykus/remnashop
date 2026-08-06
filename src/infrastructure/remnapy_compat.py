"""
Правки моделей remnapy под то, что панель присылает на самом деле.

Импортируется ради побочного эффекта: патчи должны примениться до первой
валидации вебхука. Держим их отдельно, чтобы было видно, где мы расходимся
с SDK и почему — при обновлении remnapy этот файл проверяют первым.
"""

from typing import Optional
from uuid import UUID

from loguru import logger
from remnapy.models.webhook import HwidUserDeviceDto


def _relax_hwid_user_device() -> None:
    """
    Делает userUuid необязательным в событиях об устройствах.

    Панель перестала присылать это поле (замечено 06.08.2026 на событиях
    удаления устройства): валидация падала, вебхук отвечал 401, панель уходила
    в повторы. Бот при этом не узнавал об удалении, и у пользователя оставался
    занятый слот устройства — с этим и шли в поддержку.

    Само поле нам не нужно: пользователь приходит отдельным полем события,
    а handle_device_event берёт его оттуда.
    """
    field = HwidUserDeviceDto.model_fields.get("user_uuid")
    if field is None or not field.is_required():
        return

    field.annotation = Optional[UUID]
    field.default = None
    HwidUserDeviceDto.model_rebuild(force=True)
    logger.debug("Patched HwidUserDeviceDto.user_uuid to be optional")


_relax_hwid_user_device()
