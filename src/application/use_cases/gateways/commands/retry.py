"""
Допроведение платежей, у которых не прошла выдача подписки.

Деньги в таких платежах уже списаны, а подписка не выдана — обычно потому,
что в момент оплаты не ответила панель. Раньше платёж так и оставался в
FAILED, пока о нём не узнавали из жалобы клиента. Теперь бот сам повторяет
выдачу, пока не пройдёт окно PURCHASE_RETRY_WINDOW.

Повтор — это то же проведение, что запускает вебхук шлюза, и безопасен по
той же причине: переход FAILED -> COMPLETED атомарен, партнёрская доля
защищена уникальным ключом, чек и реферальная награда выдаются только после
успешной выдачи подписки.
"""

from datetime import datetime, timezone

from loguru import logger

from src.application.common import Interactor
from src.application.common.dao import TransactionDao
from src.application.dto import UserDto
from src.core.enums import TransactionStatus

from .payment import PURCHASE_RETRY_WINDOW, ProcessPayment, ProcessPaymentDto


class RetryFailedPurchases(Interactor[None, int]):
    required_permission = None

    def __init__(self, transaction_dao: TransactionDao, process_payment: ProcessPayment) -> None:
        self.transaction_dao = transaction_dao
        self.process_payment = process_payment

    async def _execute(self, actor: UserDto, data: None) -> int:
        since = datetime.now(timezone.utc) - PURCHASE_RETRY_WINDOW
        failed = await self.transaction_dao.get_failed_purchases_since(since)

        for transaction in failed:
            try:
                await self.process_payment.system(
                    ProcessPaymentDto(
                        payment_id=transaction.payment_id,
                        new_transaction_status=TransactionStatus.COMPLETED,
                        gateway_type=transaction.gateway_type,
                    )
                )
            except Exception as e:
                # Подробности уже в логе проведения. Глушим здесь, чтобы
                # один застрявший платёж не останавливал остальные и чтобы
                # задача не падала: падение задачи — это ещё одно сообщение
                # владельцу каждые десять минут.
                logger.info(f"Failed purchase '{transaction.payment_id}' still not delivered: {e!r}")

        if failed:
            logger.info(f"Retried {len(failed)} failed purchase(s)")
        return len(failed)
