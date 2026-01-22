from typing import Optional, Protocol, runtime_checkable

from src.application.dto import AnyGatewaySettingsDto, PaymentGatewayDto
from src.core.enums import Currency, PaymentGatewayType


@runtime_checkable
class PaymentGatewayDao(Protocol):
    async def create(self, gateway: PaymentGatewayDto) -> PaymentGatewayDto: ...

    async def get_by_type(
        self,
        gateway_type: PaymentGatewayType,
    ) -> Optional[PaymentGatewayDto]: ...

    async def get_active_by_currency(self, currency: Currency) -> list[PaymentGatewayDto]: ...

    async def get_all(self, only_active: bool = False) -> list[PaymentGatewayDto]: ...

    async def update_settings(
        self,
        gateway_type: PaymentGatewayType,
        settings: AnyGatewaySettingsDto,
    ) -> Optional[PaymentGatewayDto]: ...

    async def set_active_status(
        self,
        gateway_type: PaymentGatewayType,
        is_active: bool,
    ) -> None: ...

    async def count_active(self) -> int: ...
