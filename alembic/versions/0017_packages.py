"""add packages and package change log

Revision ID: 0017_packages
Revises: 0016_credit_ledger_evt_len
Create Date: 2026-01-18 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0017_packages"
down_revision = "0016_credit_ledger_evt_len"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "packages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("package_key", sa.String(length=16), nullable=False),
        sa.Column("seconds", sa.Integer(), nullable=False),
        sa.Column("approx_attempts_5s", sa.Integer(), nullable=False),
        sa.Column("manual_price_uzs", sa.Integer(), nullable=False),
        sa.Column("stars_price", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_by_admin_id", sa.BigInteger(), nullable=True),
        sa.UniqueConstraint("package_key", name="uq_packages_key"),
    )
    op.create_table(
        "package_change_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("admin_id", sa.BigInteger(), nullable=False),
        sa.Column("package_key", sa.String(length=16), nullable=False),
        sa.Column("old_manual_price_uzs", sa.Integer(), nullable=True),
        sa.Column("new_manual_price_uzs", sa.Integer(), nullable=True),
        sa.Column("old_stars_price", sa.Integer(), nullable=True),
        sa.Column("new_stars_price", sa.Integer(), nullable=True),
        sa.Column("old_is_active", sa.Boolean(), nullable=True),
        sa.Column("new_is_active", sa.Boolean(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_package_change_created", "package_change_log", ["created_at"])
    op.alter_column("packages", "is_active", server_default=None)
    op.alter_column("packages", "updated_at", server_default=None)
    op.alter_column("package_change_log", "created_at", server_default=None)

    op.execute(
        """
        INSERT INTO packages (
            package_key,
            seconds,
            approx_attempts_5s,
            manual_price_uzs,
            stars_price,
            is_active,
            updated_at
        )
        VALUES
            ('BASIC', 500, 100, 15000, 80, true, NOW()),
            ('STANDARD', 1500, 300, 35000, 220, true, NOW()),
            ('PRO', 3000, 600, 60000, 400, true, NOW())
        """
    )


def downgrade() -> None:
    op.drop_index("ix_package_change_created", table_name="package_change_log")
    op.drop_table("package_change_log")
    op.drop_table("packages")
