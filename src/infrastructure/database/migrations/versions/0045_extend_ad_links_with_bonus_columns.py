"""extend ad_links with bonus columns and create ad_link_users

Revision ID: 0045
Revises: 0044
Create Date: 2026-05-18

Upstream's 0029 already created the base ad_links table (id, name, code, is_active, timestamps)
and added ad_link_id FK to users. This migration adds our extra columns and the tracking table.
"""

import sqlalchemy as sa
from alembic import op

revision = "0045"
down_revision = "0044"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ad_links",
        sa.Column("bonus_points", sa.Integer, nullable=False, server_default="0"),
    )
    op.add_column(
        "ad_links",
        sa.Column("bonus_days", sa.Integer, nullable=False, server_default="0"),
    )
    op.add_column(
        "ad_links",
        sa.Column("bonus_discount_pct", sa.Integer, nullable=False, server_default="0"),
    )
    op.add_column(
        "ad_links",
        sa.Column("clicks_count", sa.Integer, nullable=False, server_default="0"),
    )

    op.create_table(
        "ad_link_users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "ad_link_id",
            sa.Integer,
            sa.ForeignKey("ad_links.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_telegram_id", sa.BigInteger, nullable=False),
        sa.Column("bonus_issued", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.UniqueConstraint("ad_link_id", "user_telegram_id", name="uq_ad_link_users"),
    )
    op.create_index("ix_ad_link_users_ad_link_id", "ad_link_users", ["ad_link_id"])
    op.create_index(
        "ix_ad_link_users_user_telegram_id", "ad_link_users", ["user_telegram_id"]
    )


def downgrade() -> None:
    op.drop_table("ad_link_users")
    op.drop_column("ad_links", "clicks_count")
    op.drop_column("ad_links", "bonus_discount_pct")
    op.drop_column("ad_links", "bonus_days")
    op.drop_column("ad_links", "bonus_points")
