"""add TRAFFIC_RESET to purchase_type enum

Revision ID: 0043
Revises: 0042
Create Date: 2026-04-20
"""
from typing import Union

from alembic import op

revision: str = "0043"
down_revision: Union[str, None] = "0042"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE purchase_type ADD VALUE IF NOT EXISTS 'TRAFFIC_RESET'")


def downgrade() -> None:
    pass
