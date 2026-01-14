"""words_manage_indexes

Revision ID: 0004_words_manage_indexes
Revises: 0003_srs_training_reminders
Create Date: 2024-01-01 00:00:03.000000

"""
from alembic import op


revision = "0004_words_manage_indexes"
down_revision = "0003_srs_training_reminders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_words_user_created", "words", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_words_user_created", table_name="words")
