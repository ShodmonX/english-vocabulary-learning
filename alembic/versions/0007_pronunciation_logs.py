"""add pronunciation logs

Revision ID: 0007_pronunciation_logs
Revises: 0006_user_settings
Create Date: 2025-02-10 00:00:01.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_pronunciation_logs"
down_revision = "0006_user_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pronunciation_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("pronunciation_logs")
