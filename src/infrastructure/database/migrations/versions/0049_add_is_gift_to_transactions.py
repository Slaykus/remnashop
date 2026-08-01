"""add is_gift to transactions

Revision ID: 0049
Revises: 0048
Create Date: 2026-08-01
"""

import sqlalchemy as sa
from alembic import op

revision = "0049"
down_revision = "0048"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    exists = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
            "WHERE table_name='transactions' AND column_name='is_gift')"
        )
    ).scalar()
    if not exists:
        # server_default обязателен: в таблице уже есть транзакции, и NOT NULL
        # без значения по умолчанию не даст добавить колонку.
        op.add_column(
            "transactions",
            sa.Column("is_gift", sa.Boolean(), nullable=False, server_default=sa.false()),
        )


def downgrade() -> None:
    op.drop_column("transactions", "is_gift")
