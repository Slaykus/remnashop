"""promo text format

Revision ID: 0056
Revises: 0055
Create Date: 2026-09-03
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0056"
down_revision = "0055"
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


def _has_type(conn, name: str) -> bool:
    return bool(
        conn.execute(
            sa.text("SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = :n)"),
            {"n": name},
        ).scalar()
    )


def upgrade() -> None:
    conn = op.get_bind()

    # Пусто у всех записей, заведённых до rich-сообщений: они хранят разметку
    # телеграма и уходят как раньше. Заполнять не нужно — пустое читается
    # как HTML.
    if not _has_type(conn, "text_format"):
        op.execute("CREATE TYPE text_format AS ENUM ('HTML', 'MARKDOWN')")

    if not _has_column(conn, "ad_links", "promo_format"):
        op.add_column(
            "ad_links",
            sa.Column(
                "promo_format",
                postgresql.ENUM(name="text_format", create_type=False),
                nullable=True,
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _has_column(conn, "ad_links", "promo_format"):
        op.drop_column("ad_links", "promo_format")
    # Тип оставляем: удалять его безопасно только если им больше никто не
    # пользуется, а проверять это в откате дороже, чем оставить лишний тип.
