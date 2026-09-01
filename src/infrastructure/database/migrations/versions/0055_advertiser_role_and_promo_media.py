"""advertiser role and promo media type

Revision ID: 0055
Revises: 0054
Create Date: 2026-08-29
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0055"
down_revision = "0054"
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

    # Роль рекламного партнёра: раздел рекламы и ничего больше.
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'ADVERTISER'")

    # Промо-сообщение умело только фото. Тип вложения храним отдельно, а
    # file_id остаётся в promo_photo_id — старые записи без типа читаются
    # как фото, поэтому заполнять их не нужно.
    if not _has_type(conn, "media_type"):
        op.execute("CREATE TYPE media_type AS ENUM ('PHOTO', 'VIDEO', 'DOCUMENT', 'GIF')")

    if not _has_column(conn, "ad_links", "promo_media_type"):
        op.add_column(
            "ad_links",
            sa.Column(
                "promo_media_type",
                postgresql.ENUM(name="media_type", create_type=False),
                nullable=True,
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _has_column(conn, "ad_links", "promo_media_type"):
        op.drop_column("ad_links", "promo_media_type")
    # Тип и значение перечня ролей не убираем: их может использовать другая
    # таблица, а ALTER TYPE ... DROP VALUE в Postgres не существует.
