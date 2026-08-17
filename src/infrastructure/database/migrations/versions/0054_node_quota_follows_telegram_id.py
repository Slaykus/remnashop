"""node quota follows telegram_id on rename

Revision ID: 0054
Revises: 0053
Create Date: 2026-08-17
"""

import sqlalchemy as sa
from alembic import op

revision = "0054"
down_revision = "0053"
branch_labels = None
depends_on = None

_TABLE = "user_node_quota"
# Имя досталось от прежнего названия таблицы и в базе так и осталось.
_FK = "user_yandex_quota_user_telegram_id_fkey"


def _fk_exists(conn, name: str) -> bool:
    # Без ::regclass намеренно: приведение типа сталкивается с плейсхолдером
    # и запрос до базы не доходит.
    return bool(
        conn.execute(
            sa.text(
                "SELECT EXISTS (SELECT 1 FROM pg_constraint c "
                "JOIN pg_class t ON t.oid = c.conrelid "
                "WHERE c.conname = :n AND t.relname = :t)"
            ),
            {"n": name, "t": _TABLE},
        ).scalar()
    )


def upgrade() -> None:
    """
    Разрешить смену telegram_id у пользователя с записью о квоте.

    Ключ ссылается на users.telegram_id, а он меняется при привязке телеграма:
    аккаунт сайта живёт под псевдо-id вида -38 и получает настоящий. Без
    каскада по UPDATE база отклоняла переименование, и привязка падала целиком —
    человек видел «сервис временно недоступен» и не мог связать аккаунты
    вообще никогда, потому что запись о квоте сама уже не исчезнет.
    """
    conn = op.get_bind()
    if not _fk_exists(conn, _FK):
        return

    op.drop_constraint(_FK, _TABLE, type_="foreignkey")
    op.create_foreign_key(
        _FK,
        _TABLE,
        "users",
        ["user_telegram_id"],
        ["telegram_id"],
        ondelete="CASCADE",
        onupdate="CASCADE",
    )


def downgrade() -> None:
    conn = op.get_bind()
    if not _fk_exists(conn, _FK):
        return

    op.drop_constraint(_FK, _TABLE, type_="foreignkey")
    op.create_foreign_key(
        _FK,
        _TABLE,
        "users",
        ["user_telegram_id"],
        ["telegram_id"],
        ondelete="CASCADE",
    )
