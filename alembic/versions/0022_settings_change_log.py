"""add settings_change_log

Revision ID: 0022_settings_change_log
Revises: 0021_bot_admins
Create Date: 2026-01-20 10:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0022_settings_change_log"
down_revision = "0021_bot_admins"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "settings_change_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("admin_id", sa.BigInteger(), nullable=False),
        sa.Column("setting_key", sa.String(length=64), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("settings_change_log")
