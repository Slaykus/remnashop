"""
Докупка одного устройства к действующей подписке.

Живёт здесь, а не в экране бота, потому что покупателей двое: телеграм и
сайт. Считать цену в двух местах — значит однажды посчитать её по-разному,
а это тот самый класс расхождений, ради устранения которого тарифы и были
сведены к одной формуле.
"""

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from typing import Final, Optional

from loguru import logger

from src.application.common import Interactor
from src.application.common.dao import (
    PaymentGatewayDao,
    PlanDao,
    SettingsDao,
    SubscriptionDao,
)
from src.application.common.policy import Permission
from src.application.dto import PlanDto, PriceDetailsDto, UserDto
from src.application.services.device_pricing import (
    MAX_ADDON_DEVICES,
    extra_devices_price,
    monthly_rate,
    one_more_device_price,
)
from src.application.services.pricing import PricingService
from src.application.use_cases.gateways.commands.payment import CreatePayment, CreatePaymentDto
from src.core.enums import Currency, PaymentGatewayType, PurchaseType
from src.core.exceptions import PriceNotFoundError


@dataclass(frozen=True)
class DeviceAddonMethod:
    """Способ оплаты и цена одного устройства в его валюте."""

    gateway_type: PaymentGatewayType
    amount: Decimal
    currency: str


@dataclass(frozen=True)
class DeviceAddonOffer:
    """
    Что можно предложить человеку прямо сейчас.

    'state' отвечает, почему нельзя, если нельзя: докупка выключена в
    настройках, упёрлись в потолок, не осталось оплаченных дней или нет ни
    одного способа оплаты с ценой в своей валюте.
    """

    state: str
    current_limit: int
    new_total: int
    days_left: int
    expire_at: Optional[datetime]
    max_devices: int
    amount_rub: Decimal
    monthly_rub: int
    monthly_total_rub: Decimal
    methods: list[DeviceAddonMethod]

    @property
    def can_pay(self) -> bool:
        return self.state == "OK"


@dataclass(frozen=True)
class DeviceAddonPaymentResult:
    """Счёт и то, что о нём надо показать человеку."""

    payment_id: str
    payment_url: Optional[str]
    amount: Decimal
    currency: str
    new_total: int
    days_left: int


@dataclass(frozen=True)
class GetDeviceAddonOfferDto:
    """
    Какие шлюзы рассматривать.

    Нужно сайту: в браузере нечем платить звёздами, и показать их там
    значило бы нарисовать кнопку, которая никуда не ведёт. Отбор делается
    здесь, а не над готовым ответом, чтобы 'state' описывал ровно тот
    список способов, который спрашивающий и получил.
    """

    exclude_gateways: frozenset[PaymentGatewayType] = frozenset()


@dataclass(frozen=True)
class CreateDeviceAddonPaymentDto:
    gateway_type: PaymentGatewayType
    return_url: Optional[str] = None


class DeviceAddonError(Exception):
    """Докупить нельзя, и причина названа в сообщении."""


def _gateway_amount(
    pricing: PricingService,
    plan: Optional[PlanDto],
    currency: Currency,
    amount_rub: Decimal,
) -> Optional[Decimal]:
    """
    Цена в валюте шлюза.

    Пусто означает, что у тарифа нет цены в этой валюте и пересчитывать не
    от чего. Такой способ оплаты просто не показываем: лучше не предложить
    его вовсе, чем назвать цену наугад.
    """
    if amount_rub <= 0:
        return None
    if plan is None:
        return None
    try:
        return pricing.convert_from_rub(plan, amount_rub, currency)
    except (PriceNotFoundError, ValueError):
        return None


class GetDeviceAddonOffer(Interactor[Optional[GetDeviceAddonOfferDto], DeviceAddonOffer]):
    """Сколько стоит следующее устройство и чем за него можно заплатить."""

    required_permission = Permission.PUBLIC

    def __init__(
        self,
        subscription_dao: SubscriptionDao,
        payment_gateway_dao: PaymentGatewayDao,
        plan_dao: PlanDao,
        settings_dao: SettingsDao,
        pricing: PricingService,
    ) -> None:
        self.subscription_dao = subscription_dao
        self.payment_gateway_dao = payment_gateway_dao
        self.plan_dao = plan_dao
        self.settings_dao = settings_dao
        self.pricing = pricing

    async def _execute(
        self, actor: UserDto, data: Optional[GetDeviceAddonOfferDto] = None
    ) -> DeviceAddonOffer:
        excluded = data.exclude_gateways if data else frozenset()
        subscription = await self.subscription_dao.get_current(actor.id)
        if not subscription:
            raise DeviceAddonError(f"No subscription for user '{actor.remna_name}'")

        current_limit = subscription.device_limit
        new_total = current_limit + 1
        days_left = subscription.days_left

        amount_rub = one_more_device_price(
            current_devices=current_limit,
            term_days=subscription.plan_snapshot.duration,
            days=days_left,
        )

        plan = await self.plan_dao.get_by_id(subscription.plan_snapshot.id)

        methods = []
        for gateway in await self.payment_gateway_dao.get_active():
            if gateway.type in excluded:
                continue
            amount = _gateway_amount(self.pricing, plan, gateway.currency, amount_rub)
            if amount is None:
                continue
            methods.append(
                DeviceAddonMethod(
                    gateway_type=gateway.type,
                    amount=amount,
                    currency=gateway.currency.symbol,
                )
            )

        settings = await self.settings_dao.get()

        # Выключатель из админки. Проверяем здесь, а не на каждом экране:
        # в боте кнопку прячет меню, и без общей проверки сайт продолжал бы
        # продавать устройства после того, как их отключили.
        if not settings.extra.device_addon_enabled:
            state = "DISABLED"
        elif current_limit <= 0:
            state = "UNLIMITED"
        elif new_total > MAX_ADDON_DEVICES:
            state = "CEILING"
        elif days_left <= 0 or amount_rub <= 0:
            state = "NOTHING_TO_PAY"
        elif not methods:
            state = "NO_METHODS"
        else:
            state = "OK"

        return DeviceAddonOffer(
            state=state,
            current_limit=current_limit,
            new_total=new_total,
            days_left=days_left,
            expire_at=subscription.expire_at,
            max_devices=MAX_ADDON_DEVICES,
            amount_rub=amount_rub,
            monthly_rub=int(monthly_rate(new_total)),
            monthly_total_rub=extra_devices_price(new_total, term_days=30),
            methods=methods,
        )


class CreateDeviceAddonPayment(
    Interactor[CreateDeviceAddonPaymentDto, DeviceAddonPaymentResult]
):
    """
    Счёт на одно дополнительное устройство.

    Сумма считается здесь заново, а не принимается снаружи: между показом
    цены и нажатием кнопки проходит время, а платят за оставшиеся дни.
    Принять сумму от клиента значило бы позволить назначить её самому.
    """

    required_permission = Permission.PUBLIC

    def __init__(
        self,
        subscription_dao: SubscriptionDao,
        payment_gateway_dao: PaymentGatewayDao,
        plan_dao: PlanDao,
        settings_dao: SettingsDao,
        pricing: PricingService,
        create_payment: CreatePayment,
    ) -> None:
        self.subscription_dao = subscription_dao
        self.payment_gateway_dao = payment_gateway_dao
        self.plan_dao = plan_dao
        self.settings_dao = settings_dao
        self.pricing = pricing
        self.create_payment = create_payment

    async def _execute(
        self, actor: UserDto, data: CreateDeviceAddonPaymentDto
    ) -> DeviceAddonPaymentResult:
        settings = await self.settings_dao.get()
        if not settings.extra.device_addon_enabled:
            raise DeviceAddonError("Device purchase is disabled in settings")

        subscription = await self.subscription_dao.get_current(actor.id)
        gateway = await self.payment_gateway_dao.get_by_type(data.gateway_type)

        if not subscription or not gateway:
            raise DeviceAddonError(
                f"No subscription or gateway '{data.gateway_type}' "
                f"for user '{actor.remna_name}'"
            )

        current_limit = subscription.device_limit
        new_total = current_limit + 1
        days_left = subscription.days_left

        if current_limit <= 0 or new_total > MAX_ADDON_DEVICES or days_left <= 0:
            raise DeviceAddonError(
                f"Device purchase not available for user '{actor.remna_name}': "
                f"limit={current_limit}, days_left={days_left}"
            )

        amount_rub = one_more_device_price(
            current_devices=current_limit,
            term_days=subscription.plan_snapshot.duration,
            days=days_left,
        )
        plan = await self.plan_dao.get_by_id(subscription.plan_snapshot.id)
        amount = _gateway_amount(self.pricing, plan, gateway.currency, amount_rub)

        if amount is None or amount <= 0:
            raise DeviceAddonError(
                f"No price in '{gateway.currency}' for a device "
                f"for user '{actor.remna_name}'"
            )

        # Снимок несёт новый общий потолок и остаток дней: по первому
        # проведение поймёт, сколько устройств оплачено, второй попадёт в
        # описание счёта.
        snapshot = replace(
            subscription.plan_snapshot, device_limit=new_total, duration=days_left
        )

        result = await self.create_payment(
            actor,
            CreatePaymentDto(
                plan_snapshot=snapshot,
                # Скидку не применяем. Разовая выдана под покупку подписки,
                # и списать её на устройство за восемьдесят рублей значило
                # бы сжечь человеку выгоду в разы большую.
                pricing=PriceDetailsDto(
                    original_amount=amount,
                    discount_percent=0,
                    final_amount=amount,
                ),
                purchase_type=PurchaseType.DEVICES,
                gateway_type=data.gateway_type,
                return_url=data.return_url,
            ),
        )

        logger.info(
            f"{actor.log} Created device payment '{result.id}': "
            f"{new_total} devices for {days_left} day(s), {amount}{gateway.currency.symbol}"
        )
        return DeviceAddonPaymentResult(
            payment_id=str(result.id),
            payment_url=result.url,
            amount=amount,
            currency=gateway.currency.symbol,
            new_total=new_total,
            days_left=days_left,
        )


# Регистрируется отдельно от SUBSCRIPTION_USE_CASES, а не в общем списке
# пакета. Этот модуль тянет за собой выставление счёта, а оно — начисление
# реферальных наград, которое само возвращается в пакет подписки. Пока
# список лежал в '__init__.py', импорт пакета начинался с этой цепочки и
# упирался в полупостроенный модуль наград: бот падал на старте.
DEVICE_ADDON_USE_CASES: Final[tuple[type[Interactor], ...]] = (
    GetDeviceAddonOffer,
    CreateDeviceAddonPayment,
)
