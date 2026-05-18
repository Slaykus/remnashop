"""rename user_yandex_quota to user_node_quota

Revision ID: 0027
Revises: 0026
Create Date: 2026-05-18
"""

from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("user_yandex_quota", "user_node_quota")
    op.execute(
        "ALTER INDEX IF EXISTS ix_user_yandex_quota_user_telegram_id "
        "RENAME TO ix_user_node_quota_user_telegram_id"
    )
    op.execute(
        "ALTER INDEX IF EXISTS uq_user_yandex_quota_user_telegram_id "
        "RENAME TO uq_user_node_quota_user_telegram_id"
    )


def downgrade() -> None:
    op.rename_table("user_node_quota", "user_yandex_quota")
    op.execute(
        "ALTER INDEX IF EXISTS ix_user_node_quota_user_telegram_id "
        "RENAME TO ix_user_yandex_quota_user_telegram_id"
    )
    op.execute(
        "ALTER INDEX IF EXISTS uq_user_node_quota_user_telegram_id "
        "RENAME TO uq_user_yandex_quota_user_telegram_id"
    )
