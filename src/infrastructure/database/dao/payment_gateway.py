from typing import Any, Optional

from adaptix import Retort
from adaptix.conversion import ConversionRetort
from loguru import logger
from redis.asyncio import Redis
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.common.dao import PaymentGatewayDao
from src.application.dto import AnyGatewaySettingsDto, PaymentGatewayDto
from src.core.enums import Currency, PaymentGatewayType
from src.infrastructure.database.models import PaymentGateway


class PaymentGatewayDaoImpl(PaymentGatewayDao):
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

        self._convert_to_dto = self.conversion_retort.get_converter(
            PaymentGateway,
            PaymentGatewayDto,
        )
        self._convert_to_dto_list = self.conversion_retort.get_converter(
            list[PaymentGateway],
            list[PaymentGatewayDto],
        )

    async def create(self, gateway: PaymentGatewayDto) -> PaymentGatewayDto:
        gateway_data = self.retort.dump(gateway)
        db_gateway = PaymentGateway(**gateway_data)
        self.session.add(db_gateway)
        await self.session.flush()

        logger.debug(f"Payment gateway '{gateway.type}' created")
        return self._convert_to_dto(db_gateway)

    async def get_by_type(self, gateway_type: PaymentGatewayType) -> Optional[PaymentGatewayDto]:
        stmt = select(PaymentGateway).where(PaymentGateway.type == gateway_type)
        db_gateway = await self.session.scalar(stmt)

        if db_gateway:
            logger.debug(f"Payment gateway '{gateway_type}' found")
            return self._convert_to_dto(db_gateway)

        logger.debug(f"Payment gateway '{gateway_type}' not found")
        return None

    async def get_active_by_currency(self, currency: Currency) -> list[PaymentGatewayDto]:
        stmt = (
            select(PaymentGateway)
            .where(PaymentGateway.is_active == True)  # noqa: E712
            .where(PaymentGateway.currency == currency)
            .order_by(PaymentGateway.order_index.asc())
        )
        result = await self.session.scalars(stmt)
        db_gateways = list(result.all())

        logger.debug(f"Retrieved '{len(db_gateways)}' active gateways for currency '{currency}'")
        return self._convert_to_dto_list(db_gateways)

    async def get_all(self, only_active: bool = False) -> list[PaymentGatewayDto]:
        stmt = select(PaymentGateway).order_by(PaymentGateway.order_index.asc())
        if only_active:
            stmt = stmt.where(PaymentGateway.is_active == True)  # noqa: E712

        result = await self.session.scalars(stmt)
        db_gateways = list(result.all())

        logger.debug(
            f"Retrieved '{len(db_gateways)}' gateways with only_active status '{only_active}'"
        )
        return self._convert_to_dto_list(db_gateways)

    async def update_settings(
        self,
        gateway_type: PaymentGatewayType,
        settings: AnyGatewaySettingsDto,
    ) -> Optional[PaymentGatewayDto]:
        if not settings.changed_data:
            logger.warning("No changes detected in PaymentGateway settings, skipping update")
            return await self.get_by_type(settings.type)

        values_to_update = {}

        for key, value in settings.changed_data.items():
            column = getattr(AnyGatewaySettingsDto, key)

            if isinstance(value, dict):
                dumped = {k: self.retort.dump(v, Any) for k, v in value.items()}
                values_to_update[key] = column.concat(dumped)
            else:
                values_to_update[key] = self.retort.dump(value)

        stmt = (
            update(PaymentGateway)
            .where(PaymentGateway.type == gateway_type)
            .values(**values_to_update)
            .returning(PaymentGateway)
        )
        db_gateway = await self.session.scalar(stmt)

        if db_gateway:
            logger.debug(f"Settings for gateway '{gateway_type}' updated")
            return self._convert_to_dto(db_gateway)

        logger.warning(f"Failed to update settings: gateway '{gateway_type}' not found")
        return None

    async def set_active_status(self, gateway_type: PaymentGatewayType, is_active: bool) -> None:
        stmt = (
            update(PaymentGateway)
            .where(PaymentGateway.type == gateway_type)
            .values(is_active=is_active)
        )
        await self.session.execute(stmt)
        logger.debug(f"Gateway '{gateway_type}' active status set to '{is_active}'")

    async def count_active(self) -> int:
        stmt = (
            select(func.count()).select_from(PaymentGateway).where(PaymentGateway.is_active == True)  # noqa: E712
        )
        count = await self.session.scalar(stmt) or 0

        logger.debug(f"Total active gateways count is '{count}'")
        return count
