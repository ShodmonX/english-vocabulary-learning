"""add bot_admins

Revision ID: 0021_bot_admins
Revises: 0020_remove_daily_limits
Create Date: 2026-01-20 10:05:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0021_bot_admins"
down_revision = "0020_remove_daily_limits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "bot_admins",
        sa.Column("tg_user_id", sa.BigInteger(), primary_key=True),
        sa.Column("first_name", sa.String(length=128), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("added_by", sa.BigInteger(), nullable=False),
        sa.Column(
            "added_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("is_owner", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_table("bot_admins")
