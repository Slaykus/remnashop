"""add promo fields to ad_links

Revision ID: 0046
Revises: 0045
Create Date: 2026-05-18
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0046"
down_revision = "0045"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("ad_links", sa.Column("promo_text", sa.Text, nullable=True))
    op.add_column(
        "ad_links",
        sa.Column("promo_buttons", JSONB, nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("ad_links", "promo_buttons")
    op.drop_column("ad_links", "promo_text")
