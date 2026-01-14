"""initial

Revision ID: 0001_init
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("telegram_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("daily_goal", sa.Integer(), nullable=False),
        sa.Column("reminder_time", sa.Time(), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )

    op.create_table(
        "words",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("word", sa.String(length=128), nullable=False),
        sa.Column("translation", sa.String(length=256), nullable=False),
        sa.Column("example", sa.Text(), nullable=True),
        sa.Column("pos", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("user_id", "word", name="uq_words_user_word"),
    )

    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("word_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("stage", sa.Integer(), nullable=False),
        sa.Column("due_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["word_id"], ["words.id"]),
    )

    op.create_table(
        "review_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("word_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["word_id"], ["words.id"]),
    )


def downgrade() -> None:
    op.drop_table("review_logs")
    op.drop_table("reviews")
    op.drop_table("words")
    op.drop_table("users")
