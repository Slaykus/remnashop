from typing import Optional

from .base import BaseConfig


class YandexConfig(BaseConfig, env_prefix="YANDEX_"):
    squad_uuid: Optional[str] = None  # if None, entire feature is disabled
    node_uuids: str = ""              # comma-separated UUIDs of Yandex nodes
    monthly_limit_gb: int = 50
    dry_run: bool = True              # MUST be True by default — safe mode
    circuit_breaker_pct: int = 20    # abort if >N% users would be restricted

    @property
    def node_uuid_list(self) -> list[str]:
        return [u.strip() for u in self.node_uuids.split(",") if u.strip()]

    @property
    def enabled(self) -> bool:
        return self.squad_uuid is not None and bool(self.node_uuid_list)
