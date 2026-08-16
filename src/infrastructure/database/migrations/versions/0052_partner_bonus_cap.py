"""partner max bonus days

Revision ID: 0052
Revises: 0051
Create Date: 2026-08-16
"""

import sqlalchemy as sa
from alembic import op

revision = "0052"
down_revision = "0051"
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
    # Потолок бонуса, который партнёр вправе поставить на свою ссылку.
    # Ноль по умолчанию: пока владелец не разрешил явно, партнёр раздавать
    # чужие дни не может. Разрешение — предмет договорённости, как и ставка.
    if not _has_column(conn, "partners", "max_bonus_days"):
        op.add_column(
            "partners",
            sa.Column("max_bonus_days", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _has_column(conn, "partners", "max_bonus_days"):
        op.drop_column("partners", "max_bonus_days")
