"""ad link one-time discount

Revision ID: 0057
Revises: 0056
Create Date: 2026-09-04
"""

import sqlalchemy as sa
from alembic import op

revision = "0057"
down_revision = "0056"
branch_labels = None
depends_on = None


def _has_column(conn, table: str, column: str) -> bool:
    return bool(
        conn.execute(
            sa.text(
                "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                "WHERE table_name=:t AND column_name=:c)"
            ),
            {"t": table, "c": column},
        ).scalar()
    )


def upgrade() -> None:
    conn = op.get_bind()

    # Вторая скидка, разовая. Уходит в purchase_discount, который обнуляется
    # после первой оплаты; постоянная так и остаётся в bonus_discount_pct.
    if not _has_column(conn, "ad_links", "bonus_discount_once_pct"):
        op.add_column(
            "ad_links",
            sa.Column(
                "bonus_discount_once_pct",
                sa.Integer,
                nullable=False,
                server_default="0",
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _has_column(conn, "ad_links", "bonus_discount_once_pct"):
        op.drop_column("ad_links", "bonus_discount_once_pct")
