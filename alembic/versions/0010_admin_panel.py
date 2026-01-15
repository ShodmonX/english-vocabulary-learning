"""admin panel tables and user flags

Revision ID: 0010_admin_panel
Revises: 0009_training_session_word_id
Create Date: 2025-02-10 00:00:04.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0010_admin_panel"
down_revision = "0009_training_session_word_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=64), nullable=True))
    op.add_column(
        "users",
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.create_table(
        "quiz_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_quiz_sessions_created_at", "quiz_sessions", ["created_at"])

    op.create_table(
        "feature_flags",
        sa.Column("name", sa.String(length=64), primary_key=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )

    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("admin_user_id", sa.BigInteger(), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_admin_audit_created_at", "admin_audit_logs", ["created_at"])

    op.alter_column("users", "is_blocked", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_admin_audit_created_at", table_name="admin_audit_logs")
    op.drop_table("admin_audit_logs")

    op.drop_table("feature_flags")

    op.drop_index("ix_quiz_sessions_created_at", table_name="quiz_sessions")
    op.drop_table("quiz_sessions")

    op.drop_column("users", "is_blocked")
    op.drop_column("users", "username")
