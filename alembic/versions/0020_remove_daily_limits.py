"""remove daily limit settings

Revision ID: 0020_remove_daily_limits
Revises: 0019_app_settings
Create Date: 2026-01-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0020_remove_daily_limits"
down_revision = "0019_app_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("user_settings", "daily_limit_enabled")
    op.drop_column("user_settings", "daily_pronunciation_limit")


def downgrade() -> None:
    op.add_column(
        "user_settings",
        sa.Column("daily_pronunciation_limit", sa.Integer(), nullable=False, server_default="10"),
    )
    op.add_column(
        "user_settings",
        sa.Column("daily_limit_enabled", sa.Boolean(), nullable=False, server_default="true"),
    )
    op.alter_column("user_settings", "daily_limit_enabled", server_default=None)
    op.alter_column("user_settings", "daily_pronunciation_limit", server_default=None)
