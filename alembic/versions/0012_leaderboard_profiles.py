"""leaderboard public profiles and word count

Revision ID: 0012_leaderboard_profiles
Revises: 0011_user_streaks
Create Date: 2026-01-14 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0012_leaderboard_profiles"
down_revision = "0011_user_streaks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("word_count", sa.Integer(), nullable=False, server_default="0"))
    op.execute(
        """
        UPDATE users
        SET word_count = sub.cnt
        FROM (
            SELECT user_id, COUNT(*)::int AS cnt
            FROM words
            GROUP BY user_id
        ) AS sub
        WHERE users.id = sub.user_id
        """
    )
    op.alter_column("users", "word_count", server_default=None)

    op.create_table(
        "user_public_profiles",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("leaderboard_opt_in", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("public_name", sa.String(length=64), nullable=True),
        sa.Column("show_username", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index(
        "ix_user_public_profiles_opt_in",
        "user_public_profiles",
        ["leaderboard_opt_in"],
        unique=False,
    )
    op.create_index("ix_users_current_streak", "users", ["current_streak"], unique=False)
    op.create_index("ix_users_longest_streak", "users", ["longest_streak"], unique=False)
    op.create_index("ix_users_word_count", "users", ["word_count"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_word_count", table_name="users")
    op.drop_index("ix_users_longest_streak", table_name="users")
    op.drop_index("ix_users_current_streak", table_name="users")
    op.drop_index("ix_user_public_profiles_opt_in", table_name="user_public_profiles")
    op.drop_table("user_public_profiles")
    op.drop_column("users", "word_count")
