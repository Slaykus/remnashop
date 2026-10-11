from loguru import logger

from src.application.common import Interactor
from src.application.common.dao import BroadcastDao, TransactionDao
from src.application.common.uow import UnitOfWork
from src.application.dto import UserDto


# Через сколько гасим неоплаченный платёж.
#
# Считать надо позже, чем это делает сам шлюз, а не раньше. Пока порог был
# 30 минут, мы успевали первыми: задача ходит по расписанию */30, поэтому
# платёж гасился в возрасте от 30 до 60 минут, а ЮKassa отменяет свой
# примерно через 62. В зазор попадала поздняя оплата — подтверждение банка
# после 3-D Secure приходило в уже погашенную строку, переход
# CANCELED -> COMPLETED не предусмотрен, и деньги списывались без подписки.
#
# Сроки инвойсов у включённых шлюзов: ЮKassa около 62 минут (наблюдение),
# Heleket 30 минут (lifetime: 1800, унаследован от Cryptomus), Telegram
# Stars не истекает вовсе — у звёзд этот таймер единственное, что вообще
# закрывает платёж. Трёх часов хватает с запасом на любой из них.
#
# Поднимать порог безопасно: на строки в PENDING ничего не опирается.
# Единственный другой их читатель, get_recent_pending, живёт на своём
# пятнадцатиминутном окне, статистика по статусу не фильтрует, и ничего в
# интерфейсе на них не завязано. Это уборка мусора, а не бизнес-правило.
PENDING_CANCEL_AFTER_MINUTES: int = 180


class CancelOldTransactions(Interactor[None, None]):
    required_permission = None

    def __init__(self, uow: UnitOfWork, transaction_dao: TransactionDao) -> None:
        self.uow = uow
        self.transaction_dao = transaction_dao

    async def _execute(self, actor: UserDto, data: None) -> None:
        async with self.uow:
            await self.transaction_dao.cancel_old(PENDING_CANCEL_AFTER_MINUTES)
            await self.uow.commit()

        logger.info("Canceled old transactions from database")


class ClearOldBroadcasts(Interactor[None, None]):
    required_permission = None

    def __init__(self, uow: UnitOfWork, broadcast_dao: BroadcastDao) -> None:
        self.uow = uow
        self.broadcast_dao = broadcast_dao

    async def _execute(self, actor: UserDto, data: None) -> None:
        async with self.uow:
            await self.broadcast_dao.delete_old()
            await self.uow.commit()

        logger.info("Cleaned up old broadcasts from database")
