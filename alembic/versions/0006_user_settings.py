"""add user_settings table

Revision ID: 0006_user_settings
Revises: 0005_translation_cache
Create Date: 2025-02-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0006_user_settings"
down_revision = "0005_translation_cache"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE pronunciation_mode AS ENUM ('single', 'quiz', 'both'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE translation_engine AS ENUM ('google'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; "
        "END $$;"
    )

    op.create_table(
        "user_settings",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column(
            "learning_words_per_day",
            sa.Integer(),
            nullable=False,
            server_default="10",
        ),
        sa.Column(
            "quiz_words_per_session",
            sa.Integer(),
            nullable=False,
            server_default="10",
        ),
        sa.Column(
            "pronunciation_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "pronunciation_mode",
            postgresql.ENUM(
                "single",
                "quiz",
                "both",
                name="pronunciation_mode",
                create_type=False,
            ),
            nullable=False,
            server_default="both",
        ),
        sa.Column(
            "translation_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "translation_engine",
            postgresql.ENUM(
                "google",
                name="translation_engine",
                create_type=False,
            ),
            nullable=False,
            server_default="google",
        ),
        sa.Column(
            "auto_translation_suggest",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "daily_limit_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "daily_pronunciation_limit",
            sa.Integer(),
            nullable=False,
            server_default="10",
        ),
        sa.Column(
            "notifications_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("notification_time", sa.Time(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("user_settings")
    op.execute("DROP TYPE IF EXISTS pronunciation_mode")
    op.execute("DROP TYPE IF EXISTS translation_engine")
