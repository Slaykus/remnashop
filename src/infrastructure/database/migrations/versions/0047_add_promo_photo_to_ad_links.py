"""add promo_photo_id to ad_links

Revision ID: 0047
Revises: 0046
Create Date: 2026-05-18
"""

import sqlalchemy as sa
from alembic import op

revision = "0047"
down_revision = "0046"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    exists = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
            "WHERE table_name='ad_links' AND column_name='promo_photo_id')"
        )
    ).scalar()
    if not exists:
        op.add_column("ad_links", sa.Column("promo_photo_id", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("ad_links", "promo_photo_id")
