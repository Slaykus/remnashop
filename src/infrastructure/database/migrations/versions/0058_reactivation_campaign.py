"""reactivation campaign: discount expiry and notification log

Revision ID: 0058
Revises: 0057
Create Date: 2026-09-04
"""

import sqlalchemy as sa
from alembic import op

revision = "0058"
down_revision = "0057"
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


def _has_table(conn, name: str) -> bool:
    return bool(
        conn.execute(
            sa.text("SELECT to_regclass(:n) IS NOT NULL"), {"n": f"public.{name}"}
        ).scalar()
    )


def upgrade() -> None:
    conn = op.get_bind()

    # Срок жизни разовой скидки. Пусто — как было: скидка висит до покупки.
    # Кампании возврата нужен дедлайн, иначе «три дня» — просто слова в тексте.
    if not _has_column(conn, "users", "purchase_discount_expires_at"):
        op.add_column(
            "users",
            sa.Column("purchase_discount_expires_at", sa.DateTime(timezone=True), nullable=True),
        )

    # Журнал отправленного. Уникальность пары «человек + повод» и есть
    # защита от повторной отправки: второй раз строка просто не вставится,
    # даже если задача отработает дважды.
    if not _has_table(conn, "user_notification_log"):
        op.create_table(
            "user_notification_log",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column(
                "user_id",
                sa.Integer,
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
                index=True,
            ),
            sa.Column("kind", sa.String(64), nullable=False),
            sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
            # Что именно ушло: размер скидки, до какого числа. Нужно, чтобы
            # потом посчитать эффект, не восстанавливая его по логам бота.
            sa.Column("details", sa.JSON, nullable=True),
            sa.UniqueConstraint("user_id", "kind", name="uq_user_notification_log"),
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _has_table(conn, "user_notification_log"):
        op.drop_table("user_notification_log")
    if _has_column(conn, "users", "purchase_discount_expires_at"):
        op.drop_column("users", "purchase_discount_expires_at")
