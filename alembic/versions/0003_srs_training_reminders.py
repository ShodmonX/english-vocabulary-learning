"""srs_training_reminders

Revision ID: 0003_srs_training_reminders
Revises: 0002_telegram_id_bigint
Create Date: 2024-01-01 00:00:02.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "0003_srs_training_reminders"
down_revision = "0002_telegram_id_bigint"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("reminder_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.alter_column("users", "reminder_enabled", server_default=None)

    op.add_column("reviews", sa.Column("ease_factor", sa.Float(), nullable=False, server_default="2.5"))
    op.add_column("reviews", sa.Column("interval_days", sa.Float(), nullable=False, server_default="0"))
    op.alter_column("reviews", "ease_factor", server_default=None)
    op.alter_column("reviews", "interval_days", server_default=None)

    op.create_index("ix_reviews_user_due", "reviews", ["user_id", "due_at"], unique=False)

    op.create_table(
        "training_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("current_review_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["current_review_id"], ["reviews.id"]),
    )


def downgrade() -> None:
    op.drop_table("training_sessions")
    op.drop_index("ix_reviews_user_due", table_name="reviews")
    op.drop_column("reviews", "interval_days")
    op.drop_column("reviews", "ease_factor")
    op.drop_column("users", "reminder_enabled")
