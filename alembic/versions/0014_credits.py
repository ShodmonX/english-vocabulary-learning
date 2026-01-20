"""add credit balances and ledger

Revision ID: 0014_credits
Revises: 0013_quiz_pronunciation_results
Create Date: 2026-01-15 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0014_credits"
down_revision = "0013_quiz_pronunciation_results"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "credit_balances",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("basic_remaining_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("topup_remaining_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "next_basic_refill_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_table(
        "credit_ledger",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("event_type", sa.String(length=16), nullable=False),
        sa.Column("basic_delta_seconds", sa.Integer(), nullable=False),
        sa.Column("topup_delta_seconds", sa.Integer(), nullable=False),
        sa.Column("charge_seconds", sa.Integer(), nullable=True),
        sa.Column("audio_duration_seconds", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(length=32), nullable=True),
        sa.Column("provider_request_id", sa.String(length=128), nullable=True),
        sa.Column("admin_id", sa.BigInteger(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index(
        "ix_credit_ledger_user_created", "credit_ledger", ["user_id", "created_at"]
    )
    op.alter_column("credit_balances", "basic_remaining_seconds", server_default=None)
    op.alter_column("credit_balances", "topup_remaining_seconds", server_default=None)
    op.alter_column("credit_balances", "next_basic_refill_at", server_default=None)
    op.alter_column("credit_balances", "updated_at", server_default=None)
    op.alter_column("credit_ledger", "created_at", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_credit_ledger_user_created", table_name="credit_ledger")
    op.drop_table("credit_ledger")
    op.drop_table("credit_balances")
