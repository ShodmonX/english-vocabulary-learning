"""extend credit ledger event_type length

Revision ID: 0016_credit_ledger_evt_len
Revises: 0015_stars_payments
Create Date: 2026-01-17 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0016_credit_ledger_evt_len"
down_revision = "0015_stars_payments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("credit_ledger", "event_type", type_=sa.String(length=32))


def downgrade() -> None:
    op.alter_column("credit_ledger", "event_type", type_=sa.String(length=16))
