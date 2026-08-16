"""partner payout confirmation

Revision ID: 0053
Revises: 0052
Create Date: 2026-08-16
"""

import sqlalchemy as sa
from alembic import op

revision = "0053"
down_revision = "0052"
branch_labels = None
depends_on = None


def _has_column(conn, table: str, column: str) -> bool:
    return bool(
        conn.execute(
            sa.text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                "WHERE table_name=:t AND column_name=:c)"
            ),
            {"t": table, "c": column},
        ).scalar()
    )


def upgrade() -> None:
    conn = op.get_bind()
    # Когда партнёр подтвердил, что деньги дошли. До этого выплата остаётся
    # словом одной стороны: владелец нажал «выплатить», а перевод мог не
    # пройти — система об этом не узнала бы.
    if not _has_column(conn, "partner_payouts", "confirmed_at"):
        op.add_column(
            "partner_payouts",
            sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _has_column(conn, "partner_payouts", "confirmed_at"):
        op.drop_column("partner_payouts", "confirmed_at")
