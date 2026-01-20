"""add app settings table

Revision ID: 0019_app_settings
Revises: 0018_package_seconds
Create Date: 2026-01-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0019_app_settings"
down_revision = "0018_package_seconds"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=64), primary_key=True),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.alter_column("app_settings", "updated_at", server_default=None)


def downgrade() -> None:
    op.drop_table("app_settings")
