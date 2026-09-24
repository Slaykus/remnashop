from datetime import datetime, timezone
from decimal import ROUND_DOWN, Decimal, InvalidOperation

from loguru import logger

from src.application.dto import PlanDto, PlanDurationDto, PriceDetailsDto, UserDto
from src.application.services.device_pricing import bought_devices_price, price_in_currency
from src.core.enums import Currency
from src.core.exceptions import PriceNotFoundError


class PricingService:
    @staticmethod
    def get_live_purchase_discount(user: UserDto) -> int:
        """Разовая скидка с учётом срока.

        Публичный метод, а не внутренний: сырое поле 'purchase_discount'
        показывали в главном меню и в карточке, и человек видел «Скидка
        на покупку: 20%» через две недели после того, как она сгорела.
        Показывать скидку должен тот же расчёт, что применяет её на кассе.

        Пустая дата — скидка бессрочная, так вели себя все скидки до
        кампании возврата. Просроченная — скидки нет: обещание «сгорит
        через три дня» иначе оказалось бы неправдой в нашу же пользу.
        """
        discount = user.purchase_discount or 0
        expires_at = user.purchase_discount_expires_at
        if discount <= 0 or expires_at is None:
            return discount
        return discount if expires_at > datetime.now(timezone.utc) else 0

    def is_largest_discount_personal(self, user: UserDto) -> bool:
        personal = user.personal_discount or 0
        purchase = self.get_live_purchase_discount(user)
        return personal > 0 and personal > purchase

    def get_effective_discount(self, user: UserDto) -> int:
        purchase = self.get_live_purchase_discount(user)
        discount_percent = min(max(purchase, user.personal_discount or 0), 100)
        logger.debug(
            f"Calculated effective discount percent '{discount_percent}' for user "
            f"'{user.remna_name}' (purchase_discount='{user.purchase_discount}', "
            f"expires_at='{user.purchase_discount_expires_at}', "
            f"personal_discount='{user.personal_discount}')"
        )
        return discount_percent

    def calculate(
        self,
        user: UserDto,
        price: Decimal,
        currency: Currency,
        apply_discount: bool = True,
    ) -> PriceDetailsDto:
        logger.debug(
            f"Calculating price for amount '{price}' and currency "
            f"'{currency}' for user '{user.remna_name}'"
        )

        if price <= 0:
            logger.debug("Price is zero, returning without discount")
            return PriceDetailsDto(
                original_amount=Decimal(0),
                discount_percent=0,
                final_amount=Decimal(0),
            )

        discount_percent = self.get_effective_discount(user) if apply_discount else 0

        if discount_percent >= 100:
            logger.info(f"100% discount applied, price is free for user {user.log}")
            return PriceDetailsDto(
                original_amount=price,
                discount_percent=100,
                final_amount=Decimal(0),
            )

        discounted = price * (Decimal(100) - Decimal(discount_percent)) / Decimal(100)
        final_amount = self.apply_currency_rules(discounted, currency)

        if final_amount == price:
            discount_percent = 0

        logger.info(
            f"Price calculated: original='{price}', "
            f"discount_percent='{discount_percent}', final='{final_amount}'"
        )

        return PriceDetailsDto(
            original_amount=price,
            discount_percent=discount_percent,
            final_amount=final_amount,
        )

    # Знаков после запятой у суммы в каждой валюте: звёзды и рубли целые,
    # доллары с копейками.
    _DECIMALS: dict[Currency, int] = {
        Currency.RUB: 0,
        Currency.USD: 2,
        Currency.XTR: 0,
    }

    # Месячная цена тарифа — якорь, от которого считается курс для
    # устройств. Своих цен в валютах у них нет, а у тарифов есть.
    _ANCHOR_DAYS: int = 30

    def device_surcharge(
        self,
        plan: PlanDto,
        extra_devices: int,
        term_days: int,
        currency: Currency,
        days: int | None = None,
    ) -> Decimal:
        """
        Надбавка за докупленные устройства, в валюте оплаты.

        Считается сверх устройств самого тарифа: они уже входят в его цену,
        и добавлять их второй раз значит брать за них дважды. Сколько их у
        тарифа, берём из него же, а не от вызывающего, — так надбавку
        нельзя посчитать не от той базы.

        Пустой тариф или отсутствие его цены в нужной валюте — повод
        отказаться, а не отдать ноль: ноль здесь означает подарить
        устройство, а это ошибка, которую никто не заметит.
        """
        amount_rub = bought_devices_price(
            plan.device_limit, extra_devices, term_days, days
        )
        if amount_rub <= 0:
            return Decimal(0)
        if currency == Currency.RUB:
            return amount_rub

        anchor = plan.get_duration(self._ANCHOR_DAYS)
        if anchor is None:
            raise PriceNotFoundError(
                f"No monthly duration in plan '{plan.name}' to convert device price from"
            )

        return price_in_currency(
            amount_rub,
            anchor.get_price(Currency.RUB),
            anchor.get_price(currency),
            self._DECIMALS.get(currency, 2),
        )

    def convert_from_rub(self, plan: PlanDto, amount_rub: Decimal, currency: Currency) -> Decimal:
        """
        Рублёвую сумму — в валюту оплаты, по курсу самого тарифа.

        Отдельно от 'device_surcharge' потому, что сумма бывает уже
        посчитана: цена одного следующего устройства — это разность, и
        пересчитывать её из числа устройств заново значило бы повторить
        расчёт и однажды разойтись с ним.
        """
        if currency == Currency.RUB:
            return amount_rub

        anchor_duration = plan.get_duration(self._ANCHOR_DAYS)
        if anchor_duration is None:
            raise PriceNotFoundError(
                f"No monthly duration in plan '{plan.name}' to convert from"
            )

        return price_in_currency(
            amount_rub,
            anchor_duration.get_price(Currency.RUB),
            anchor_duration.get_price(currency),
            self._DECIMALS.get(currency, 2),
        )

    def calculate_for_duration(
        self,
        user: UserDto,
        duration: PlanDurationDto,
        currency: Currency,
        apply_discount: bool = True,
        extra_amount: Decimal = Decimal(0),
    ) -> PriceDetailsDto:
        """
        Цена срока подписки вместе с надбавкой за докупленные устройства.

        Надбавка складывается с ценой тарифа до скидки, а не после: иначе
        скидка обошла бы устройства стороной, и человек со скидкой платил
        бы за них полную цену, не понимая почему.
        """
        discount = self.get_effective_discount(user) if apply_discount else 0

        if discount >= 100 and not any(p.currency == currency for p in duration.prices):
            fallback = next((p.price for p in duration.prices), Decimal(0))
            logger.info(
                f"{user.log} 100% discount: currency '{currency}' has no price, "
                f"using fallback original amount '{fallback}'"
            )
            return self.calculate(
                user, fallback + extra_amount, currency, apply_discount=apply_discount
            )

        return self.calculate(
            user,
            duration.get_price(currency) + extra_amount,
            currency,
            apply_discount=apply_discount,
        )

    def parse_price(self, input_price: str, currency: Currency) -> Decimal:
        logger.debug(f"Parsing input price '{input_price}' for currency '{currency}'")

        try:
            price = Decimal(input_price.strip())
        except InvalidOperation:
            raise ValueError(f"Invalid numeric format provided for price: '{input_price}'")

        if price < 0:
            raise ValueError(f"Negative price provided: '{input_price}'")
        if price == 0:
            return Decimal(0)

        final_price = self.apply_currency_rules(price, currency)
        logger.debug(f"Parsed price '{final_price}' after applying currency rules")
        return final_price

    def apply_currency_rules(self, amount: Decimal, currency: Currency) -> Decimal:
        logger.debug(f"Applying currency rules for amount '{amount}' and currency '{currency}'")

        match currency:
            case Currency.XTR | Currency.RUB:
                amount = amount.to_integral_value(rounding=ROUND_DOWN)
                min_amount = Decimal(1)
            case _:
                amount = amount.quantize(Decimal("0.01"))
                amount = Decimal(f"{amount.normalize():f}")
                min_amount = Decimal("0.01")

        if amount < min_amount:
            logger.debug(f"Amount '{amount}' less than min '{min_amount}', adjusting")
            amount = min_amount

        logger.debug(f"Final amount after currency rules: '{amount}'")
        return amount
