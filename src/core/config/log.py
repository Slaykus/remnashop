from src.core.enums import LogLevel

from .base import BaseConfig


class LogConfig(BaseConfig, env_prefix="LOG_"):
    # Значения локальных переменных в traceback. У loguru это включено по
    # умолчанию, и в кадрах оказывается всё подряд — в том числе пароль от
    # базы из параметров подключения asyncpg. Логи уходят в файл, в буфер
    # админки и в уведомления об ошибках в Telegram, так что по умолчанию
    # выключено. Включать через LOG_DIAGNOSE=true, когда правда нужно.
    diagnose: bool = False
    to_file: bool = True
    level: LogLevel = LogLevel.DEBUG
    rotation: str = "100MB"  # "00:00"
    compression: str = "zip"
    retention: str = "3 days"
