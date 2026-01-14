"""translation_cache

Revision ID: 0005_translation_cache
Revises: 0004_words_manage_indexes
Create Date: 2024-01-01 00:00:04.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "0005_translation_cache"
down_revision = "0004_words_manage_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "translation_cache",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("source_text_norm", sa.String(length=256), nullable=False),
        sa.Column("source_lang", sa.String(length=8), nullable=False),
        sa.Column("target_lang", sa.String(length=8), nullable=False),
        sa.Column("translated_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "source_text_norm",
            "source_lang",
            "target_lang",
            name="uq_translation_cache_source",
        ),
    )


def downgrade() -> None:
    op.drop_table("translation_cache")
