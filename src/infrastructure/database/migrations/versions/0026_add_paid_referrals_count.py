"""add paid_referrals_count to users

Revision ID: 0026
Revises: 0025
Create Date: 2026-04-21

"""
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "0026"
down_revision: Union[str, None] = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "paid_referrals_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "paid_referrals_count")
