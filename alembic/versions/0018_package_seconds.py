"""add package seconds change log fields

Revision ID: 0018_package_seconds
Revises: 0017_packages
Create Date: 2026-01-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0018_package_seconds"
down_revision = "0017_packages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("package_change_log", sa.Column("old_seconds", sa.Integer(), nullable=True))
    op.add_column("package_change_log", sa.Column("new_seconds", sa.Integer(), nullable=True))
    op.add_column(
        "package_change_log",
        sa.Column("old_approx_attempts_5s", sa.Integer(), nullable=True),
    )
    op.add_column(
        "package_change_log",
        sa.Column("new_approx_attempts_5s", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("package_change_log", "new_approx_attempts_5s")
    op.drop_column("package_change_log", "old_approx_attempts_5s")
    op.drop_column("package_change_log", "new_seconds")
    op.drop_column("package_change_log", "old_seconds")
