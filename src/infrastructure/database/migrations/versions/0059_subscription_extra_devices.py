"""subscription: devices bought on top of the plan

Revision ID: 0059
Revises: 0058
Create Date: 2026-09-21

У подписки давно есть собственный лимит устройств, и его даже можно
поменять из админки. Но при продлении он затирается лимитом тарифа, так
что любая надбавка живёт только до конца оплаченного периода.

Здесь появляется отдельное поле — сколько устройств куплено сверх
тарифа. Оно переживает продление и им же считается цена. Отдельно от
'device_limit' потому, что выданное руками администратором не должно
превращаться в платную докупку при следующем списании.

У всех существующих подписок это ноль, то есть поведение прежнее.
"""

import sqlalchemy as sa
from alembic import op

revision = "0059"
down_revision = "0058"
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
    if not _has_column(conn, "subscriptions", "extra_devices"):
        op.add_column(
            "subscriptions",
            sa.Column(
                "extra_devices",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _has_column(conn, "subscriptions", "extra_devices"):
        op.drop_column("subscriptions", "extra_devices")
