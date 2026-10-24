"""
Решения при слиянии двух бот-аккаунтов одного человека.

Когда человек сначала платит в кабинете, а потом привязывает Telegram, у
него оказывается два аккаунта: виртуальный, на который ушёл платёж, и
настоящий. Если у настоящего уже есть своя подписка, их надо свести в одну.

Здесь только решения, без базы и панели: чей тариф остаётся и до какого
числа. Отдельно потому, что от них зависят деньги клиента, а решение проще
проверить, когда оно не перемешано с записью в базу.
"""

import math
from datetime import datetime, timedelta
from typing import Literal, Protocol


class _SubscriptionLimits(Protocol):
    traffic_limit: int
    device_limit: int
    expire_at: datetime
    is_trial: bool


def _rank(limit: int) -> float:
    """
    Лимит как число для сравнения.

    Ноль здесь значит «без ограничения» — и для трафика, и для устройств.
    Сравнивать в лоб нельзя: max() выбрал бы 5 ГБ вместо безлимита и
    понизил бы клиента ровно там, где понижать запрещено.
    """
    return math.inf if limit <= 0 else float(limit)


def dominates(a: _SubscriptionLimits, b: _SubscriptionLimits) -> bool:
    """
    Подписка a не хуже b ни по трафику, ни по устройствам и лучше хотя бы
    по одному из них.

    Сравниваются фактические лимиты подписки, а не тариф из снимка: они
    расходятся. У импортированных подписок в снимке стоит безлимитный
    трафик, а на самой подписке — 5 ГБ, и именно на них человек упирается.
    """
    a_traffic, a_devices = _rank(a.traffic_limit), _rank(a.device_limit)
    b_traffic, b_devices = _rank(b.traffic_limit), _rank(b.device_limit)
    not_worse = a_traffic >= b_traffic and a_devices >= b_devices
    better = a_traffic > b_traffic or a_devices > b_devices
    return not_worse and better


def plan_source(
    virtual: _SubscriptionLimits,
    real: _SubscriptionLimits,
    now: datetime,
) -> Literal["virtual", "real"]:
    """
    Чей тариф остаётся на общей подписке.

    Тариф берётся целиком, с одной стороны, а не лучшее по каждому лимиту
    отдельно. Сборный тариф не совпал бы ни с одним из каталога, и при
    продлении бот не нашёл бы, что продлевать.

    Понижать нельзя: если тариф телеграм-аккаунта не хуже оплаченного в
    кабинете, остаётся он. Когда лимиты расходятся в разные стороны — один
    лучше по трафику, другой по устройствам, — тоже остаётся он: решить за
    клиента, что из этого ему важнее, мы не можем, а ничего у него не
    отнимаем.
    """
    # Истёкшая подписка — уже не тариф, понижать в ней нечего.
    if real.expire_at <= now:
        return "virtual"

    # Пробный период не то, за что человек платил, и он не должен
    # перекрывать оплаченный тариф.
    if real.is_trial and not virtual.is_trial:
        return "virtual"

    if dominates(virtual, real):
        return "virtual"

    return "real"


def merged_expire_at(real_expire_at: datetime, carried_days: int, now: datetime) -> datetime:
    """
    До какого числа действует общая подписка.

    Дни отсчитываются от позднего из двух моментов: конца подписки
    телеграм-аккаунта и текущего. Прибавка к одному лишь концу подписки
    ломалась на давно истёкших: тридцать дней поверх даты полугодовой
    давности давали снова дату в прошлом, перенос отказывал, и привязать
    Telegram человек не мог вовсе.
    """
    return max(real_expire_at, now) + timedelta(days=carried_days)
