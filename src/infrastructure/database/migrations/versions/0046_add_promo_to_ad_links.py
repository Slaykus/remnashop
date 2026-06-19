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


def _col_exists(conn: sa.engine.Connection, table: str, column: str) -> bool:
    return conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
            "WHERE table_name=:t AND column_name=:c)"
        ),
        {"t": table, "c": column},
    ).scalar()  # type: ignore[return-value]


def upgrade() -> None:
    conn = op.get_bind()
    if not _col_exists(conn, "ad_links", "promo_text"):
        op.add_column("ad_links", sa.Column("promo_text", sa.Text, nullable=True))
    if not _col_exists(conn, "ad_links", "promo_buttons"):
        op.add_column(
            "ad_links",
            sa.Column("promo_buttons", JSONB, nullable=False, server_default="[]"),
        )


def downgrade() -> None:
    op.drop_column("ad_links", "promo_buttons")
    op.drop_column("ad_links", "promo_text")
