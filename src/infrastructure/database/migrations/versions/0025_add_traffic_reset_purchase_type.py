"""add TRAFFIC_RESET to purchase_type enum

Revision ID: 0025
Revises: 0024
Create Date: 2026-04-20

"""
from typing import Union

from alembic import op

revision: str = "0025"
down_revision: Union[str, None] = "0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE purchase_type ADD VALUE IF NOT EXISTS 'TRAFFIC_RESET'")


def downgrade() -> None:
    # PostgreSQL does not support removing enum values directly.
    # A full enum recreation would be needed; skip for safety.
    pass
