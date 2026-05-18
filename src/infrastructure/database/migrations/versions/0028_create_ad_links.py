"""create ad_links and ad_link_users tables

Revision ID: 0028
Revises: 0027
Create Date: 2026-05-18
"""

import sqlalchemy as sa
from alembic import op

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ad_links",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String, nullable=False, unique=True),
        sa.Column("name", sa.String, nullable=False),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("bonus_points", sa.Integer, nullable=False, server_default="0"),
        sa.Column("bonus_days", sa.Integer, nullable=False, server_default="0"),
        sa.Column("bonus_discount_pct", sa.Integer, nullable=False, server_default="0"),
        sa.Column("clicks_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )
    op.create_index("ix_ad_links_code", "ad_links", ["code"], unique=True)

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
    op.drop_table("ad_links")
