"""add level test tables

Revision ID: 0023_level_test_tables
Revises: 0022_settings_change_log
Create Date: 2026-02-20 10:30:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0023_level_test_tables"
down_revision = "0022_settings_change_log"
branch_labels = None
depends_on = None


def _seed_questions() -> None:
    questions = sa.table(
        "level_test_questions",
        sa.column("level_tag", sa.String(length=2)),
        sa.column("difficulty", sa.Integer()),
        sa.column("type", sa.String(length=16)),
        sa.column("prompt", sa.Text()),
        sa.column("choices", postgresql.JSONB(astext_type=sa.Text())),
        sa.column("correct_answer", sa.Text()),
        sa.column("accepted_answers", postgresql.JSONB(astext_type=sa.Text())),
        sa.column("explanation", sa.Text()),
        sa.column("is_active", sa.Boolean()),
    )
    op.bulk_insert(
        questions,
        [
            {
                "level_tag": "A1",
                "difficulty": 1,
                "type": "MCQ",
                "prompt": "She ___ to school every day.",
                "choices": ["go", "goes", "going", "went"],
                "correct_answer": "goes",
                "accepted_answers": None,
                "explanation": "Simple present with third-person singular takes -s.",
                "is_active": True,
            },
            {
                "level_tag": "A2",
                "difficulty": 2,
                "type": "MCQ",
                "prompt": "We have lived here ___ 2018.",
                "choices": ["for", "since", "from", "by"],
                "correct_answer": "since",
                "accepted_answers": None,
                "explanation": "Use 'since' with a specific starting point in time.",
                "is_active": True,
            },
            {
                "level_tag": "A2",
                "difficulty": 2,
                "type": "MCQ",
                "prompt": "If I ___ time, I will call you.",
                "choices": ["had", "have", "will have", "am having"],
                "correct_answer": "have",
                "accepted_answers": None,
                "explanation": "First conditional uses present simple in the if-clause.",
                "is_active": True,
            },
            {
                "level_tag": "A1",
                "difficulty": 1,
                "type": "MCQ",
                "prompt": "He is ___ than his brother.",
                "choices": ["tall", "taller", "more tall", "tallest"],
                "correct_answer": "taller",
                "accepted_answers": None,
                "explanation": "Use comparative adjective for two people.",
                "is_active": True,
            },
            {
                "level_tag": "B1",
                "difficulty": 3,
                "type": "MCQ",
                "prompt": "By the time we arrived, they ___ dinner.",
                "choices": ["finished", "have finished", "had finished", "were finishing"],
                "correct_answer": "had finished",
                "accepted_answers": None,
                "explanation": "Past perfect shows an earlier past action.",
                "is_active": True,
            },
            {
                "level_tag": "B1",
                "difficulty": 3,
                "type": "MCQ",
                "prompt": "The book ___ by Orwell.",
                "choices": ["wrote", "was written", "is writing", "has wrote"],
                "correct_answer": "was written",
                "accepted_answers": None,
                "explanation": "Passive voice: was + past participle.",
                "is_active": True,
            },
            {
                "level_tag": "B2",
                "difficulty": 4,
                "type": "MCQ",
                "prompt": "Neither of the answers ___ correct.",
                "choices": ["are", "were", "is", "be"],
                "correct_answer": "is",
                "accepted_answers": None,
                "explanation": "'Neither' is singular in formal usage.",
                "is_active": True,
            },
            {
                "level_tag": "B2",
                "difficulty": 4,
                "type": "MCQ",
                "prompt": "I wish I ___ more free time.",
                "choices": ["have", "had", "would have", "am having"],
                "correct_answer": "had",
                "accepted_answers": None,
                "explanation": "Use past simple after 'wish' for present unreal situations.",
                "is_active": True,
            },
            {
                "level_tag": "C1",
                "difficulty": 5,
                "type": "MCQ",
                "prompt": "Hardly ___ the train left when we reached the station.",
                "choices": ["had", "has", "did", "was"],
                "correct_answer": "had",
                "accepted_answers": None,
                "explanation": "Inversion pattern: Hardly had ... when ...",
                "is_active": True,
            },
            {
                "level_tag": "B2",
                "difficulty": 4,
                "type": "MCQ",
                "prompt": "Scarcely any water ___ left.",
                "choices": ["are", "were", "is", "have"],
                "correct_answer": "is",
                "accepted_answers": None,
                "explanation": "'Water' is an uncountable singular noun.",
                "is_active": True,
            },
            {
                "level_tag": "B2",
                "difficulty": 4,
                "type": "MCQ",
                "prompt": "Not only he but also his friends ___ coming.",
                "choices": ["is", "are", "was", "be"],
                "correct_answer": "are",
                "accepted_answers": None,
                "explanation": "Agreement follows the nearest subject ('friends').",
                "is_active": True,
            },
            {
                "level_tag": "C1",
                "difficulty": 5,
                "type": "MCQ",
                "prompt": "She suggested that he ___ earlier.",
                "choices": ["arrives", "arrived", "arrive", "will arrive"],
                "correct_answer": "arrive",
                "accepted_answers": None,
                "explanation": "Subjunctive base form follows 'suggested that'.",
                "is_active": True,
            },
            {
                "level_tag": "A2",
                "difficulty": 2,
                "type": "MCQ",
                "prompt": "The meeting was postponed ___ Monday.",
                "choices": ["to", "for", "until", "at"],
                "correct_answer": "until",
                "accepted_answers": None,
                "explanation": "'Postponed until Monday' is the natural collocation.",
                "is_active": True,
            },
            {
                "level_tag": "B1",
                "difficulty": 3,
                "type": "MCQ",
                "prompt": "We are looking forward to ___ you.",
                "choices": ["see", "seeing", "saw", "seen"],
                "correct_answer": "seeing",
                "accepted_answers": None,
                "explanation": "'To' in this phrase is a preposition, so use -ing.",
                "is_active": True,
            },
            {
                "level_tag": "B2",
                "difficulty": 4,
                "type": "MCQ",
                "prompt": "It is high time you ___ responsibility.",
                "choices": ["take", "took", "have taken", "will take"],
                "correct_answer": "took",
                "accepted_answers": None,
                "explanation": "Use past simple after 'it's high time'.",
                "is_active": True,
            },
            {
                "level_tag": "C1",
                "difficulty": 5,
                "type": "MCQ",
                "prompt": "No sooner ___ I sat down than the phone rang.",
                "choices": ["had", "did", "have", "was"],
                "correct_answer": "had",
                "accepted_answers": None,
                "explanation": "Inversion pattern: No sooner had ... than ...",
                "is_active": True,
            },
            {
                "level_tag": "B1",
                "difficulty": 3,
                "type": "MCQ",
                "prompt": "The project must ___ by Friday.",
                "choices": ["complete", "completed", "be completed", "be completing"],
                "correct_answer": "be completed",
                "accepted_answers": None,
                "explanation": "Modal + be + past participle for passive.",
                "is_active": True,
            },
            {
                "level_tag": "B2",
                "difficulty": 4,
                "type": "MCQ",
                "prompt": "He denied ___ the window.",
                "choices": ["break", "breaking", "to break", "broke"],
                "correct_answer": "breaking",
                "accepted_answers": None,
                "explanation": "'Deny' is followed by a gerund.",
                "is_active": True,
            },
            {
                "level_tag": "A1",
                "difficulty": 1,
                "type": "TYPING",
                "prompt": "Type one word: opposite of 'ancient'.",
                "choices": None,
                "correct_answer": "modern",
                "accepted_answers": ["modern"],
                "explanation": None,
                "is_active": True,
            },
            {
                "level_tag": "A2",
                "difficulty": 2,
                "type": "TYPING",
                "prompt": "Type one word: past tense of 'teach'.",
                "choices": None,
                "correct_answer": "taught",
                "accepted_answers": ["taught"],
                "explanation": None,
                "is_active": True,
            },
            {
                "level_tag": "A2",
                "difficulty": 2,
                "type": "TYPING",
                "prompt": "Type one word: a person who writes books.",
                "choices": None,
                "correct_answer": "author",
                "accepted_answers": ["author", "writer"],
                "explanation": None,
                "is_active": True,
            },
            {
                "level_tag": "A1",
                "difficulty": 1,
                "type": "TYPING",
                "prompt": "Fill the blank with one word: I'm interested ___ music.",
                "choices": None,
                "correct_answer": "in",
                "accepted_answers": ["in"],
                "explanation": None,
                "is_active": True,
            },
            {
                "level_tag": "A2",
                "difficulty": 2,
                "type": "TYPING",
                "prompt": "Type one word: comparative form of 'good'.",
                "choices": None,
                "correct_answer": "better",
                "accepted_answers": ["better"],
                "explanation": None,
                "is_active": True,
            },
            {
                "level_tag": "A1",
                "difficulty": 1,
                "type": "TYPING",
                "prompt": "Fill the blank with one word: They arrived ___ time.",
                "choices": None,
                "correct_answer": "on",
                "accepted_answers": ["on"],
                "explanation": None,
                "is_active": True,
            },
            {
                "level_tag": "B1",
                "difficulty": 3,
                "type": "TYPING",
                "prompt": "Type one word: noun form of 'decide'.",
                "choices": None,
                "correct_answer": "decision",
                "accepted_answers": ["decision"],
                "explanation": None,
                "is_active": True,
            },
            {
                "level_tag": "A2",
                "difficulty": 2,
                "type": "TYPING",
                "prompt": "Fill the blank with one word: She has been working here ___ two years.",
                "choices": None,
                "correct_answer": "for",
                "accepted_answers": ["for"],
                "explanation": None,
                "is_active": True,
            },
            {
                "level_tag": "B1",
                "difficulty": 3,
                "type": "TYPING",
                "prompt": "Type one word: opposite of 'increase'.",
                "choices": None,
                "correct_answer": "decrease",
                "accepted_answers": ["decrease", "reduce"],
                "explanation": None,
                "is_active": True,
            },
            {
                "level_tag": "A2",
                "difficulty": 2,
                "type": "TYPING",
                "prompt": "Fill the blank with two words: Please ___ the lights before leaving.",
                "choices": None,
                "correct_answer": "turn off",
                "accepted_answers": ["turn off", "switch off"],
                "explanation": None,
                "is_active": True,
            },
            {
                "level_tag": "B1",
                "difficulty": 3,
                "type": "TYPING",
                "prompt": "Type one word: adjective form of 'danger'.",
                "choices": None,
                "correct_answer": "dangerous",
                "accepted_answers": ["dangerous"],
                "explanation": None,
                "is_active": True,
            },
            {
                "level_tag": "B1",
                "difficulty": 3,
                "type": "TYPING",
                "prompt": "Fill the blank with one word: If it ___ tomorrow, we'll stay home.",
                "choices": None,
                "correct_answer": "rains",
                "accepted_answers": ["rains"],
                "explanation": None,
                "is_active": True,
            },
        ],
    )


def upgrade() -> None:
    op.create_table(
        "level_test_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("level_tag", sa.String(length=2), nullable=False),
        sa.Column("difficulty", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("choices", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("correct_answer", sa.Text(), nullable=True),
        sa.Column("accepted_answers", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("difficulty >= 1 AND difficulty <= 5", name="ck_level_test_questions_difficulty"),
    )
    op.create_index(
        "ix_level_test_questions_active_type",
        "level_test_questions",
        ["is_active", "type"],
    )

    op.create_table(
        "level_test_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("ui_mode", sa.String(length=16), nullable=False, server_default="LINEAR"),
        sa.Column("current_index", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="ACTIVE"),
        sa.Column("answered_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("correct_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("flagged_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("score_pct", sa.Float(), nullable=True),
        sa.Column("level_estimate", sa.String(length=2), nullable=True),
        sa.Column("confidence", sa.String(length=16), nullable=True),
        sa.Column("chat_id", sa.BigInteger(), nullable=True),
        sa.Column("message_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index(
        "ix_level_test_attempts_user_created",
        "level_test_attempts",
        ["user_id", "created_at"],
    )
    op.create_index(
        "uq_level_test_attempts_one_active_per_user",
        "level_test_attempts",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
    )

    op.create_table(
        "level_test_attempt_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "attempt_id",
            sa.Integer(),
            sa.ForeignKey("level_test_attempts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("index", sa.Integer(), nullable=False),
        sa.Column(
            "question_id",
            sa.Integer(),
            sa.ForeignKey("level_test_questions.id"),
            nullable=False,
        ),
        sa.Column("flagged", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("skipped", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("answered_at", sa.DateTime(), nullable=True),
        sa.Column("answer_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.UniqueConstraint("attempt_id", "index", name="uq_level_test_attempt_items_attempt_index"),
    )
    op.create_index(
        "ix_level_test_attempt_items_attempt",
        "level_test_attempt_items",
        ["attempt_id"],
    )

    _seed_questions()

    op.alter_column("level_test_questions", "is_active", server_default=None)
    op.alter_column("level_test_questions", "created_at", server_default=None)
    op.alter_column("level_test_attempts", "ui_mode", server_default=None)
    op.alter_column("level_test_attempts", "current_index", server_default=None)
    op.alter_column("level_test_attempts", "started_at", server_default=None)
    op.alter_column("level_test_attempts", "status", server_default=None)
    op.alter_column("level_test_attempts", "answered_count", server_default=None)
    op.alter_column("level_test_attempts", "correct_count", server_default=None)
    op.alter_column("level_test_attempts", "skipped_count", server_default=None)
    op.alter_column("level_test_attempts", "flagged_count", server_default=None)
    op.alter_column("level_test_attempts", "created_at", server_default=None)
    op.alter_column("level_test_attempts", "updated_at", server_default=None)
    op.alter_column("level_test_attempt_items", "flagged", server_default=None)
    op.alter_column("level_test_attempt_items", "skipped", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_level_test_attempt_items_attempt", table_name="level_test_attempt_items")
    op.drop_table("level_test_attempt_items")
    op.drop_index("uq_level_test_attempts_one_active_per_user", table_name="level_test_attempts")
    op.drop_index("ix_level_test_attempts_user_created", table_name="level_test_attempts")
    op.drop_table("level_test_attempts")
    op.drop_index("ix_level_test_questions_active_type", table_name="level_test_questions")
    op.drop_table("level_test_questions")
