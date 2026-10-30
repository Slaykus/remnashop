"""transactions: where the payment was started — bot or web cabinet

Revision ID: 0061
Revises: 0060
Create Date: 2026-10-31

Админке нужна разбивка оплат по источнику: бот или кабинет. Раньше это
нигде не записывалось. Колонка только добавляется и может быть пустой —
у прошлых платежей источник неизвестен, и выдумывать его нельзя.
"""

import sqlalchemy as sa
from alembic import op

revision = "0061"
down_revision = "0060"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("transactions", sa.Column("source", sa.String(length=16), nullable=True))


def downgrade() -> None:
    op.drop_column("transactions", "source")
