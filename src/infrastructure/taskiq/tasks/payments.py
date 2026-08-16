from uuid import UUID

from dishka.integrations.taskiq import FromDishka, inject

from src.application.use_cases.gateways.commands.payment import ProcessPayment, ProcessPaymentDto
from src.application.use_cases.misc.commands.maintenance import CancelOldTransactions
from src.application.use_cases.partner.commands.manage import MarkPartnerEarningsAvailable
from src.core.enums import PaymentGatewayType, TransactionStatus
from src.infrastructure.taskiq.broker import broker


@broker.task()
@inject(patch_module=True)
async def handle_payment_transaction_task(
    payment_id: UUID,
    payment_status: TransactionStatus,
    gateway_type: PaymentGatewayType,
    process_payment: FromDishka[ProcessPayment],
) -> None:
    await process_payment.system(
        ProcessPaymentDto(
            payment_id=payment_id,
            new_transaction_status=payment_status,
            gateway_type=gateway_type,
        )
    )


@broker.task(schedule=[{"cron": "*/30 * * * *"}])
@inject(patch_module=True)
async def cancel_old_transactions_task(
    cancel_old_transactions: FromDishka[CancelOldTransactions],
) -> None:
    await cancel_old_transactions.system()


@broker.task(schedule=[{"cron": "17 * * * *"}])
@inject(patch_module=True)
async def mark_partner_earnings_available_task(
    mark_available: FromDishka[MarkPartnerEarningsAvailable],
) -> None:
    """
    Раз в час переводит отлежавшие начисления в доступные к выплате.

    Не в полночь и не в ноль минут: в эти моменты и так толпятся другие
    задачи, а спешки здесь нет — счёт идёт на дни удержания, не на минуты.
    """
    await mark_available.system()
