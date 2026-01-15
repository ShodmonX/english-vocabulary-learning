"""add user streak fields

Revision ID: 0011_user_streaks
Revises: 0010_admin_panel
Create Date: 2025-02-10 00:00:05.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0011_user_streaks"
down_revision = "0010_admin_panel"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("current_streak", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("longest_streak", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("users", sa.Column("last_review_date", sa.Date(), nullable=True))
    op.alter_column("users", "current_streak", server_default=None)
    op.alter_column("users", "longest_streak", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "last_review_date")
    op.drop_column("users", "longest_streak")
    op.drop_column("users", "current_streak")
