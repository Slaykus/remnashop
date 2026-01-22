from typing import Any

from adaptix import Retort
from adaptix.conversion import ConversionRetort
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.common.dao import SettingsDao
from src.application.dto import SettingsDto
from src.core.constants import TTL_6H
from src.infrastructure.database.models import Settings
from src.infrastructure.redis.cache import invalidate_cache, provide_cache
from src.infrastructure.redis.keys import SETTINGS_PREFIX


class SettingsDaoImpl(SettingsDao):
    def __init__(
        self,
        session: AsyncSession,
        retort: Retort,
        conversion_retort: ConversionRetort,
        redis: Redis,
    ) -> None:
        self.session = session
        self.retort = retort
        self.conversion_retort = conversion_retort
        self.redis = redis

        self._convert_to_dto = self.conversion_retort.get_converter(Settings, SettingsDto)

    async def create_default(self) -> SettingsDto:
        settings_data = self.retort.dump(SettingsDto())
        db_settings = Settings(**settings_data)
        self.session.add(db_settings)

        await self.session.flush()
        await self.session.commit()

        logger.debug("Default settings record created in database")
        return self._convert_to_dto(db_settings)

    @provide_cache(prefix=SETTINGS_PREFIX, ttl=TTL_6H)
    async def get(self) -> SettingsDto:
        stmt = select(Settings).limit(1)
        db_settings = await self.session.scalar(stmt)

        if not db_settings:
            logger.debug("Settings not found, creating default")
            return await self.create_default()

        logger.debug("Global settings retrieved")
        return self._convert_to_dto(db_settings)

    @invalidate_cache(key_builder=SETTINGS_PREFIX)
    async def update(self, settings: SettingsDto) -> SettingsDto:
        if not settings.changed_data:
            logger.warning("No changes detected in settings, skipping update")
            return await self.get()

        values_to_update = {}

        for key, value in settings.changed_data.items():
            column = getattr(Settings, key)

            if isinstance(value, dict):
                dumped = {k: self.retort.dump(v, Any) for k, v in value.items()}
                values_to_update[key] = column.concat(dumped)
            else:
                values_to_update[key] = self.retort.dump(value)

        stmt = (
            update(Settings)
            .where(Settings.id == settings.id)
            .values(**values_to_update)
            .returning(Settings)
        )
        db_settings = await self.session.scalar(stmt)

        if not db_settings:
            logger.warning(f"Failed to update settings with ID '{settings.id}': record not found")
            return await self.get()

        logger.debug(f"Settings updated with keys '{list(values_to_update.keys())}'")
        return self._convert_to_dto(db_settings)
