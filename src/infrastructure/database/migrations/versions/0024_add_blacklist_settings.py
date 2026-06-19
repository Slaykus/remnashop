from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0024"
down_revision: Union[str, None] = "0023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_BLACKLIST = '{"blocked_ids": [], "sources": []}'


def upgrade() -> None:
    conn = op.get_bind()
    exists = conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
            "WHERE table_name='settings' AND column_name='blacklist')"
        )
    ).scalar()
    if not exists:
        op.add_column(
            "settings",
            sa.Column(
                "blacklist",
                postgresql.JSONB(),
                nullable=True,
            ),
        )
    op.execute(
        f"UPDATE settings SET blacklist = '{DEFAULT_BLACKLIST}'::jsonb WHERE blacklist IS NULL"
    )
    if not exists:
        op.alter_column("settings", "blacklist", nullable=False)


def downgrade() -> None:
    op.drop_column("settings", "blacklist")
