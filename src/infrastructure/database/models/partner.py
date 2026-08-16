"""
Партнёрская программа: условия, начисления и выплаты.

Отличие от реферальной системы в том, что здесь речь о деньгах. Отсюда
устройство: начисление считается один раз в момент подтверждения платежа
и дальше не пересчитывается. Запрос задним числом «все оплаты этого
человека» для аналитики годится, для выплат — нет: он меняется со
временем и способен зачесть один платёж двум партнёрам сразу.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseSql
from .timestamp import TimestampMixin


class Partner(BaseSql, TimestampMixin):
    """
    Условия конкретного партнёра.

    Ставка и сроки лежат здесь, а не в коде: договорённости с крупным
    блогером и с маленьким каналом будут разными, и менять их через выкатку
    новой версии бота недопустимо.
    """

    __tablename__ = "partners"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )

    # Доля партнёра со всех платежей приведённого клиента, включая продления.
    rate_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, server_default="35.00"
    )
    # Сколько дней начисление ждёт, прежде чем станет доступным к выплате.
    # Нужно, чтобы возврат платежа не превращался в долг партнёра.
    hold_days: Mapped[int] = mapped_column(Integer, nullable=False, server_default="7")
    # Ниже этой суммы выплата не оформляется.
    min_payout: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, server_default="500.00"
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    # Куда и как платить. Свободный текст: способы у всех разные, и
    # раскладывать их по колонкам сейчас значило бы гадать.
    payout_details: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    # Когда партнёр попросил выплату. Сбрасывается при её оформлении.
    payout_requested_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )


class PartnerEarning(BaseSql):
    """
    Начисление за один платёж.

    Строка неизменна: сумма и ставка запоминаются такими, какими были в
    момент начисления. Если партнёру потом поднимут ставку, прошлые
    начисления обязаны остаться прежними — иначе правка условий задним
    числом переписывает уже согласованные и выплаченные суммы.
    """

    __tablename__ = "partner_earnings"
    __table_args__ = (
        # Один платёж — одно начисление. Защита от повторной обработки
        # вебхука и от зачёта платежа двум партнёрам сразу.
        UniqueConstraint("transaction_id", name="uq_partner_earnings_transaction"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    partner_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("partners.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    transaction_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("transactions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    # Кого привёл партнёр. Храним, чтобы показать воронку без обращения к
    # платежам и чтобы начисление пережило удаление транзакции.
    referred_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    # Ставка на момент начисления, а не текущая ставка партнёра.
    rate_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    payment_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # pending — держим, available — можно выплачивать, paid — выплачено,
    # canceled — платёж вернули.
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default="pending")
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    payout_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("partner_payouts.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )


class PartnerPayout(BaseSql):
    """Факт выплаты: что и когда отдано партнёру."""

    __tablename__ = "partner_payouts"

    id: Mapped[int] = mapped_column(primary_key=True)
    partner_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("partners.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    # Кто отметил выплату. Нужно, когда партнёров ведёт не один человек.
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
