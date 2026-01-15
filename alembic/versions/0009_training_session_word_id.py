"""switch training_sessions current_review_id to current_word_id

Revision ID: 0009_training_session_word_id
Revises: 0008_sm2_srs_fields
Create Date: 2025-02-10 00:00:03.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_training_session_word_id"
down_revision = "0008_sm2_srs_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("training_sessions", sa.Column("current_word_id", sa.Integer(), nullable=True))
    op.drop_constraint(
        "training_sessions_current_review_id_fkey",
        "training_sessions",
        type_="foreignkey",
    )
    op.drop_column("training_sessions", "current_review_id")
    op.create_foreign_key(
        "training_sessions_current_word_id_fkey",
        "training_sessions",
        "words",
        ["current_word_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "training_sessions_current_word_id_fkey",
        "training_sessions",
        type_="foreignkey",
    )
    op.add_column(
        "training_sessions",
        sa.Column("current_review_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "training_sessions_current_review_id_fkey",
        "training_sessions",
        "reviews",
        ["current_review_id"],
        ["id"],
    )
    op.drop_column("training_sessions", "current_word_id")
