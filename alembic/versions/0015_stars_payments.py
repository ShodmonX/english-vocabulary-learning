"""add stars payments and ledger fields

Revision ID: 0015_stars_payments
Revises: 0014_credits
Create Date: 2026-01-16 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0015_stars_payments"
down_revision = "0014_credits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("credit_ledger", sa.Column("package_id", sa.String(length=32), nullable=True))
    op.add_column(
        "credit_ledger", sa.Column("provider_payment_id", sa.String(length=128), nullable=True)
    )
    op.add_column("credit_ledger", sa.Column("amount_stars", sa.Integer(), nullable=True))
    op.add_column("credit_ledger", sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True))

    op.create_table(
        "stars_payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("package_id", sa.String(length=32), nullable=False),
        sa.Column("payload", sa.String(length=128), nullable=False),
        sa.Column("amount_stars", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("credited_at", sa.DateTime(), nullable=True),
        sa.Column("telegram_charge_id", sa.String(length=128), nullable=True),
        sa.Column("raw_update", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.UniqueConstraint("payload", name="uq_stars_payments_payload"),
    )
    op.alter_column("stars_payments", "status", server_default=None)
    op.alter_column("stars_payments", "created_at", server_default=None)


def downgrade() -> None:
    op.drop_table("stars_payments")
    op.drop_column("credit_ledger", "meta")
    op.drop_column("credit_ledger", "amount_stars")
    op.drop_column("credit_ledger", "provider_payment_id")
    op.drop_column("credit_ledger", "package_id")
