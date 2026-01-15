"""add sm2 srs fields on words and review logs

Revision ID: 0008_sm2_srs_fields
Revises: 0007_pronunciation_logs
Create Date: 2025-02-10 00:00:02.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_sm2_srs_fields"
down_revision = "0007_pronunciation_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("words", sa.Column("srs_repetitions", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("words", sa.Column("srs_interval_days", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("words", sa.Column("srs_ease_factor", sa.Float(), nullable=False, server_default="2.5"))
    op.add_column(
        "words",
        sa.Column("srs_due_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )
    op.add_column("words", sa.Column("srs_last_review_at", sa.DateTime(), nullable=True))
    op.add_column("words", sa.Column("srs_lapses", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_words_user_srs_due", "words", ["user_id", "srs_due_at"])

    op.add_column("review_logs", sa.Column("q", sa.Integer(), nullable=True))
    op.add_column("review_logs", sa.Column("ef_before", sa.Float(), nullable=True))
    op.add_column("review_logs", sa.Column("ef_after", sa.Float(), nullable=True))
    op.add_column("review_logs", sa.Column("interval_before", sa.Integer(), nullable=True))
    op.add_column("review_logs", sa.Column("interval_after", sa.Integer(), nullable=True))

    op.execute(
        "UPDATE words SET "
        "srs_repetitions = COALESCE(reviews.stage, 0), "
        "srs_interval_days = COALESCE(reviews.interval_days, 0), "
        "srs_ease_factor = COALESCE(reviews.ease_factor, 2.5), "
        "srs_due_at = COALESCE(reviews.due_at, now()), "
        "srs_last_review_at = COALESCE(reviews.updated_at, NULL) "
        "FROM reviews WHERE reviews.word_id = words.id"
    )


def downgrade() -> None:
    op.drop_index("ix_words_user_srs_due", table_name="words")
    op.drop_column("words", "srs_repetitions")
    op.drop_column("words", "srs_interval_days")
    op.drop_column("words", "srs_ease_factor")
    op.drop_column("words", "srs_due_at")
    op.drop_column("words", "srs_last_review_at")
    op.drop_column("words", "srs_lapses")
    op.drop_column("review_logs", "q")
    op.drop_column("review_logs", "ef_before")
    op.drop_column("review_logs", "ef_after")
    op.drop_column("review_logs", "interval_before")
    op.drop_column("review_logs", "interval_after")
