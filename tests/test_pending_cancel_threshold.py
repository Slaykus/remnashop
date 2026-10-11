"""
Неоплаченный платёж гасим позже шлюза, а не раньше.

Переход CANCELED -> COMPLETED не предусмотрен намеренно: отменённый платёж
не должен оживать. Но пока наш таймер срабатывал раньше шлюза, поздняя
оплата попадала в уже погашенную строку, и деньги списывались без
подписки. Один клиент в это окно почти попал: его платёж мы погасили в
00:00, а ЮKassa отменила свой только в 00:08.

Срок привязан к срокам инвойсов у шлюзов, и связь эта нигде, кроме
комментария, не выражена — поэтому она проверяется здесь.
"""

from src.application.use_cases.misc.commands.maintenance import (
    PENDING_CANCEL_AFTER_MINUTES,
)
from src.infrastructure.payment_gateways.cryptomus import CryptomusGateway
from src.infrastructure.payment_gateways.heleket import HeleketGateway

# Сколько живёт инвойс у включённых шлюзов, в минутах.
#
# ЮKassa — наблюдение по проду: 30 отмен из 49 приходят на 62-й минуте.
# Heleket — lifetime: 1800 секунд, унаследован от Cryptomus.
# Telegram Stars в список не входит: инвойс-ссылка не истекает, и для неё
# наш таймер — единственное, что закрывает платёж, то есть порог может
# быть любым и чем позже, тем лучше.
GATEWAY_INVOICE_MINUTES = {
    "YOOKASSA": 62,
    "HELEKET": 30,
}


def test_threshold_outlives_every_gateway_invoice() -> None:
    longest = max(GATEWAY_INVOICE_MINUTES.values())
    assert PENDING_CANCEL_AFTER_MINUTES > longest, (
        "Гасим раньше, чем истекает инвойс: поздняя оплата попадёт в "
        "погашенную строку и деньги спишутся без подписки"
    )


def test_threshold_keeps_a_margin() -> None:
    # Запас нужен не на красоту: задача ходит по расписанию */30, поэтому
    # фактический возраст гашения гуляет на полчаса вокруг порога.
    longest = max(GATEWAY_INVOICE_MINUTES.values())
    assert PENDING_CANCEL_AFTER_MINUTES >= longest + 60


def test_heleket_invoice_lifetime_comes_from_cryptomus() -> None:
    # Рассуждение про 30 минут у Heleket держится на наследовании: своего
    # payload у него нет. Переопределят — срок станет неизвестным, и
    # порог окажется подобран непонятно под что.
    assert (
        HeleketGateway._create_payment_payload is CryptomusGateway._create_payment_payload
    ), "У Heleket появился свой payload — проверьте в нём lifetime"
