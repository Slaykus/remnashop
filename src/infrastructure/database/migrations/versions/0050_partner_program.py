"""partner program: partners, earnings, payouts, ad link owner

Revision ID: 0050
Revises: 0049
Create Date: 2026-08-16
"""

import sqlalchemy as sa
from alembic import op

revision = "0050"
down_revision = "0049"
branch_labels = None
depends_on = None


def _has_table(conn, name: str) -> bool:
    return bool(
        conn.execute(
            sa.text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name=:n)"),
            {"n": name},
        ).scalar()
    )


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

    # Роль хранится перечнем Postgres, поэтому новое значение нужно добавить
    # и в тип. IF NOT EXISTS — чтобы миграция была повторяемой.
    op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'PARTNER'")

    if not _has_table(conn, "partners"):
        op.create_table(
            "partners",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
                unique=True,
            ),
            # Условия у каждого партнёра свои. Значения по умолчанию —
            # договорённость по умолчанию, а не константа в коде.
            sa.Column("rate_pct", sa.Numeric(5, 2), nullable=False, server_default="35.00"),
            sa.Column("hold_days", sa.Integer(), nullable=False, server_default="7"),
            sa.Column("min_payout", sa.Numeric(12, 2), nullable=False, server_default="500.00"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("payout_details", sa.Text(), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_partners_user_id", "partners", ["user_id"])

    if not _has_table(conn, "partner_payouts"):
        op.create_table(
            "partner_payouts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "partner_id",
                sa.Integer(),
                sa.ForeignKey("partners.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("amount", sa.Numeric(12, 2), nullable=False),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column(
                "created_by",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        op.create_index("ix_partner_payouts_partner_id", "partner_payouts", ["partner_id"])
        op.create_index("ix_partner_payouts_created_at", "partner_payouts", ["created_at"])

    if not _has_table(conn, "partner_earnings"):
        op.create_table(
            "partner_earnings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "partner_id",
                sa.Integer(),
                sa.ForeignKey("partners.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "transaction_id",
                sa.Integer(),
                sa.ForeignKey("transactions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "referred_user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("amount", sa.Numeric(12, 2), nullable=False),
            # Ставка на момент начисления. Повышение ставки не должно
            # переписывать уже согласованные суммы.
            sa.Column("rate_pct", sa.Numeric(5, 2), nullable=False),
            sa.Column("payment_amount", sa.Numeric(12, 2), nullable=False),
            sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
            sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "payout_id",
                sa.Integer(),
                sa.ForeignKey("partner_payouts.id", ondelete="SET NULL"),
                nullable=True,
            ),
            # Один платёж — одно начисление. Защита от повторной обработки
            # вебхука и от зачёта платежа двум партнёрам сразу.
            sa.UniqueConstraint("transaction_id", name="uq_partner_earnings_transaction"),
        )
        op.create_index("ix_partner_earnings_partner_id", "partner_earnings", ["partner_id"])
        op.create_index("ix_partner_earnings_transaction_id", "partner_earnings", ["transaction_id"])
        op.create_index("ix_partner_earnings_available_at", "partner_earnings", ["available_at"])
        op.create_index("ix_partner_earnings_created_at", "partner_earnings", ["created_at"])
        op.create_index(
            "ix_partner_earnings_referred_user_id", "partner_earnings", ["referred_user_id"]
        )

    # Владелец рекламной ссылки. Пусто — своя реклама, как было; заполнено —
    # партнёрская. Nullable намеренно: существующие ссылки остаются своими.
    if not _has_column(conn, "ad_links", "owner_user_id"):
        op.add_column(
            "ad_links",
            sa.Column(
                "owner_user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
        op.create_index("ix_ad_links_owner_user_id", "ad_links", ["owner_user_id"])


def downgrade() -> None:
    conn = op.get_bind()
    if _has_column(conn, "ad_links", "owner_user_id"):
        op.drop_index("ix_ad_links_owner_user_id", table_name="ad_links")
        op.drop_column("ad_links", "owner_user_id")
    for table in ("partner_earnings", "partner_payouts", "partners"):
        if _has_table(conn, table):
            op.drop_table(table)
