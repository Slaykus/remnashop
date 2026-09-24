"""
Что сценарий докупки отвечает и кому.

Сценарий один на два клиента — бота и кабинет, — и именно поэтому его
поведение стоит закрепить: расхождение между ними теперь возможно только
здесь. Проверяем три вещи, в которых легко ошибиться: выключатель из
админки, отбор способов оплаты для сайта и отказ выставить счёт, когда
предложения нет.
"""

from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.application.services.device_pricing import MAX_ADDON_DEVICES
from src.application.use_cases.subscription.commands.add_device import (
    CreateDeviceAddonPayment,
    CreateDeviceAddonPaymentDto,
    DeviceAddonError,
    GetDeviceAddonOffer,
    GetDeviceAddonOfferDto,
)
from src.core.enums import Currency, PaymentGatewayType

ACTOR = SimpleNamespace(id=1, remna_name="tester", role=None, log="[tester]")


class _Dao:
    """Заглушка: сценарий читает у DAO ровно по одному методу."""

    def __init__(self, value):
        self._value = value

    async def get_current(self, _user_id):
        return self._value

    async def get_active(self):
        return self._value

    async def get_by_id(self, _plan_id):
        return self._value

    async def get(self):
        return self._value

    async def get_by_type(self, gateway_type):
        return next((g for g in self._value if g.type == gateway_type), None)


class _Pricing:
    """Курс не проверяем — он свой тест уже имеет. Здесь важен отбор."""

    @staticmethod
    def convert_from_rub(_plan, amount_rub: Decimal, currency: Currency) -> Decimal:
        return amount_rub if currency == Currency.RUB else amount_rub / Decimal(100)


def _subscription(device_limit: int = 2, days_left: int = 30):
    return SimpleNamespace(
        device_limit=device_limit,
        days_left=days_left,
        expire_at=None,
        plan_snapshot=SimpleNamespace(id=7, duration=30),
    )


def _gateways(*types: PaymentGatewayType):
    currencies = {
        PaymentGatewayType.TELEGRAM_STARS: Currency.XTR,
    }
    return [
        SimpleNamespace(type=t, currency=currencies.get(t, Currency.RUB)) for t in types
    ]


def _settings(enabled: bool):
    return SimpleNamespace(extra=SimpleNamespace(device_addon_enabled=enabled))


def _offer_use_case(subscription, gateways, enabled: bool = True):
    return GetDeviceAddonOffer(
        subscription_dao=_Dao(subscription),
        payment_gateway_dao=_Dao(gateways),
        plan_dao=_Dao(SimpleNamespace(name="Solo")),
        settings_dao=_Dao(_settings(enabled)),
        pricing=_Pricing(),
    )


@pytest.mark.asyncio
async def test_disabled_in_settings_beats_everything() -> None:
    # Выключатель в админке прячет кнопку в боте. Без этой проверки кабинет
    # продолжал бы продавать устройства после того, как их отключили.
    use_case = _offer_use_case(
        _subscription(), _gateways(PaymentGatewayType.YOOKASSA), enabled=False
    )
    offer = await use_case._execute(ACTOR, None)

    assert offer.state == "DISABLED"
    assert offer.can_pay is False


@pytest.mark.asyncio
async def test_excluded_gateway_leaves_the_offer() -> None:
    # Звёздами платят только внутри телеграма: сайт просит их исключить.
    use_case = _offer_use_case(
        _subscription(),
        _gateways(PaymentGatewayType.YOOKASSA, PaymentGatewayType.TELEGRAM_STARS),
    )

    full = await use_case._execute(ACTOR, None)
    for_web = await use_case._execute(
        ACTOR,
        GetDeviceAddonOfferDto(exclude_gateways=frozenset({PaymentGatewayType.TELEGRAM_STARS})),
    )

    assert {m.gateway_type for m in full.methods} == {
        PaymentGatewayType.YOOKASSA,
        PaymentGatewayType.TELEGRAM_STARS,
    }
    assert {m.gateway_type for m in for_web.methods} == {PaymentGatewayType.YOOKASSA}
    # Цена от способа оплаты не зависит — меняется только валюта.
    assert full.amount_rub == for_web.amount_rub


@pytest.mark.asyncio
async def test_last_gateway_excluded_is_not_still_payable() -> None:
    # Если отобрать нечего, предложение обязано это признать: иначе кабинет
    # нарисовал бы кнопку покупки без единого способа оплаты.
    use_case = _offer_use_case(
        _subscription(), _gateways(PaymentGatewayType.TELEGRAM_STARS)
    )
    offer = await use_case._execute(
        ACTOR,
        GetDeviceAddonOfferDto(exclude_gateways=frozenset({PaymentGatewayType.TELEGRAM_STARS})),
    )

    assert offer.methods == []
    assert offer.state == "NO_METHODS"
    assert offer.can_pay is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("subscription", "expected"),
    [
        (_subscription(device_limit=0), "UNLIMITED"),
        (_subscription(device_limit=MAX_ADDON_DEVICES), "CEILING"),
        (_subscription(days_left=0), "NOTHING_TO_PAY"),
        (_subscription(), "OK"),
    ],
)
async def test_states(subscription, expected: str) -> None:
    use_case = _offer_use_case(subscription, _gateways(PaymentGatewayType.YOOKASSA))
    offer = await use_case._execute(ACTOR, None)
    assert offer.state == expected


def _payment_use_case(subscription, gateways, enabled: bool = True):
    async def _never(*_args, **_kwargs):
        raise AssertionError("Счёт не должен выставляться, когда покупать нельзя")

    return CreateDeviceAddonPayment(
        subscription_dao=_Dao(subscription),
        payment_gateway_dao=_Dao(gateways),
        plan_dao=_Dao(SimpleNamespace(name="Solo")),
        settings_dao=_Dao(_settings(enabled)),
        pricing=_Pricing(),
        create_payment=_never,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("subscription", "enabled"),
    [
        (_subscription(), False),                            # выключено в админке
        (_subscription(device_limit=0), True),               # безлимит
        (_subscription(device_limit=MAX_ADDON_DEVICES), True),  # потолок
        (_subscription(days_left=0), True),                  # платить не за что
    ],
)
async def test_payment_refused_when_offer_is_not_payable(subscription, enabled: bool) -> None:
    # Деньги берём только там, где предложение действительно есть. Проверка
    # живёт в сценарии, а не на экране: иначе её пришлось бы повторить в
    # боте и в кабинете, и однажды одна из копий отстала бы.
    use_case = _payment_use_case(
        subscription, _gateways(PaymentGatewayType.YOOKASSA), enabled=enabled
    )

    with pytest.raises(DeviceAddonError):
        await use_case._execute(
            ACTOR, CreateDeviceAddonPaymentDto(gateway_type=PaymentGatewayType.YOOKASSA)
        )
