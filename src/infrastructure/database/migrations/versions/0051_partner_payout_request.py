"""partner payout request timestamp

Revision ID: 0051
Revises: 0050
Create Date: 2026-08-16
"""

import sqlalchemy as sa
from alembic import op

revision = "0051"
down_revision = "0050"
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
    # Отметка о запросе выплаты. Нужна, чтобы повторное нажатие не рассылало
    # уведомление заново: партнёр нажмёт трижды, а владелец получит три
    # одинаковых сообщения и перестанет их читать.
    if not _has_column(conn, "partners", "payout_requested_at"):
        op.add_column(
            "partners",
            sa.Column("payout_requested_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _has_column(conn, "partners", "payout_requested_at"):
        op.drop_column("partners", "payout_requested_at")
