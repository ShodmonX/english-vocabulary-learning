"""quiz and pronunciation results fields

Revision ID: 0013_quiz_pronunciation_results
Revises: 0012_leaderboard_profiles
Create Date: 2026-01-14 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0013_quiz_pronunciation_results"
down_revision = "0012_leaderboard_profiles"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("quiz_sessions", sa.Column("total_questions", sa.Integer(), nullable=True))
    op.add_column("quiz_sessions", sa.Column("correct", sa.Integer(), nullable=True))
    op.add_column("quiz_sessions", sa.Column("wrong", sa.Integer(), nullable=True))
    op.add_column("quiz_sessions", sa.Column("accuracy", sa.Integer(), nullable=True))
    op.add_column("quiz_sessions", sa.Column("completed_at", sa.DateTime(), nullable=True))

    op.add_column("pronunciation_logs", sa.Column("verdict", sa.String(length=16), nullable=True))
    op.add_column(
        "pronunciation_logs", sa.Column("reference_word", sa.String(length=128), nullable=True)
    )
    op.add_column("pronunciation_logs", sa.Column("mode", sa.String(length=16), nullable=True))


def downgrade() -> None:
    op.drop_column("pronunciation_logs", "mode")
    op.drop_column("pronunciation_logs", "reference_word")
    op.drop_column("pronunciation_logs", "verdict")
    op.drop_column("quiz_sessions", "completed_at")
    op.drop_column("quiz_sessions", "accuracy")
    op.drop_column("quiz_sessions", "wrong")
    op.drop_column("quiz_sessions", "correct")
    op.drop_column("quiz_sessions", "total_questions")
