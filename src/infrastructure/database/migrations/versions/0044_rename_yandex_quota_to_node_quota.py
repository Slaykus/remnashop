"""rename user_yandex_quota to user_node_quota

Revision ID: 0044
Revises: 0043
Create Date: 2026-05-18
"""

import sqlalchemy as sa
from alembic import op

revision = "0044"
down_revision = "0043"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    new_exists = conn.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='user_node_quota')")
    ).scalar()

    if new_exists:
        # Production upgrade: user_node_quota already exists from our old migration chain.
        # The intermediate user_yandex_quota table created by 0040 is redundant — drop it.
        old_exists = conn.execute(
            sa.text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='user_yandex_quota')")
        ).scalar()
        if old_exists:
            op.drop_table("user_yandex_quota")
    else:
        # Fresh install: rename the staging table to its final name.
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
