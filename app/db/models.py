from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.utcnow()


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_current_streak", "current_streak"),
        Index("ix_users_longest_streak", "longest_streak"),
        Index("ix_users_word_count", "word_count"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64))
    daily_goal: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    reminder_time: Mapped[time] = mapped_column(Time, default=time(20, 0), nullable=False)
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Tashkent")
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    current_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    longest_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_review_date: Mapped[date | None] = mapped_column(Date)
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    words: Mapped[list[Word]] = relationship("Word", back_populates="user")


class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    learning_words_per_day: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    quiz_words_per_session: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    pronunciation_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    pronunciation_mode: Mapped[str] = mapped_column(
        Enum("single", "quiz", "both", name="pronunciation_mode"),
        default="both",
        nullable=False,
    )
    translation_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    translation_engine: Mapped[str] = mapped_column(
        Enum("google", name="translation_engine"),
        default="google",
        nullable=False,
    )
    auto_translation_suggest: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    daily_limit_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    daily_pronunciation_limit: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notification_time: Mapped[time | None] = mapped_column(Time)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class UserPublicProfile(Base):
    __tablename__ = "user_public_profiles"
    __table_args__ = (Index("ix_user_public_profiles_opt_in", "leaderboard_opt_in"),)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    leaderboard_opt_in: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    public_name: Mapped[str | None] = mapped_column(String(64))
    show_username: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class Word(Base):
    __tablename__ = "words"
    __table_args__ = (
        UniqueConstraint("user_id", "word", name="uq_words_user_word"),
        Index("ix_words_user_created", "user_id", "created_at"),
        Index("ix_words_user_srs_due", "user_id", "srs_due_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    word: Mapped[str] = mapped_column(String(128), nullable=False)
    translation: Mapped[str] = mapped_column(String(256), nullable=False)
    example: Mapped[str | None] = mapped_column(Text)
    pos: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    srs_repetitions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    srs_interval_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    srs_ease_factor: Mapped[float] = mapped_column(Float, default=2.5, nullable=False)
    srs_due_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    srs_last_review_at: Mapped[datetime | None] = mapped_column(DateTime)
    srs_lapses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    user: Mapped[User] = relationship("User", back_populates="words")
    review: Mapped[Review] = relationship("Review", back_populates="word", uselist=False)


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (Index("ix_reviews_user_due", "user_id", "due_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    word_id: Mapped[int] = mapped_column(ForeignKey("words.id"), nullable=False, unique=True)
    stage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ease_factor: Mapped[float] = mapped_column(Float, default=2.5, nullable=False)
    interval_days: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    due_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    word: Mapped[Word] = relationship("Word", back_populates="review")


class ReviewLog(Base):
    __tablename__ = "review_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    word_id: Mapped[int] = mapped_column(ForeignKey("words.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    q: Mapped[int | None] = mapped_column(Integer)
    ef_before: Mapped[float | None] = mapped_column(Float)
    ef_after: Mapped[float | None] = mapped_column(Float)
    interval_before: Mapped[int | None] = mapped_column(Integer)
    interval_after: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class QuizSession(Base):
    __tablename__ = "quiz_sessions"
    __table_args__ = (Index("ix_quiz_sessions_created_at", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    total_questions: Mapped[int | None] = mapped_column(Integer)
    correct: Mapped[int | None] = mapped_column(Integer)
    wrong: Mapped[int | None] = mapped_column(Integer)
    accuracy: Mapped[int | None] = mapped_column(Integer)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PronunciationLog(Base):
    __tablename__ = "pronunciation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    verdict: Mapped[str | None] = mapped_column(String(16))
    reference_word: Mapped[str | None] = mapped_column(String(128))
    mode: Mapped[str | None] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class CreditBalance(Base):
    __tablename__ = "credit_balances"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    basic_remaining_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    topup_remaining_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_basic_refill_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class CreditLedger(Base):
    __tablename__ = "credit_ledger"
    __table_args__ = (Index("ix_credit_ledger_user_created", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    basic_delta_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    topup_delta_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    charge_seconds: Mapped[int | None] = mapped_column(Integer)
    audio_duration_seconds: Mapped[int | None] = mapped_column(Integer)
    provider: Mapped[str | None] = mapped_column(String(32))
    provider_request_id: Mapped[str | None] = mapped_column(String(128))
    package_id: Mapped[str | None] = mapped_column(String(32))
    provider_payment_id: Mapped[str | None] = mapped_column(String(128))
    admin_id: Mapped[int | None] = mapped_column(BigInteger)
    amount_stars: Mapped[int | None] = mapped_column(Integer)
    reason: Mapped[str | None] = mapped_column(Text)
    meta: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class StarsPayment(Base):
    __tablename__ = "stars_payments"
    __table_args__ = (UniqueConstraint("payload", name="uq_stars_payments_payload"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    package_id: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[str] = mapped_column(String(128), nullable=False)
    amount_stars: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime)
    credited_at: Mapped[datetime | None] = mapped_column(DateTime)
    telegram_charge_id: Mapped[str | None] = mapped_column(String(128))
    raw_update: Mapped[dict | None] = mapped_column(JSONB)


class Package(Base):
    __tablename__ = "packages"
    __table_args__ = (UniqueConstraint("package_key", name="uq_packages_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    package_key: Mapped[str] = mapped_column(String(16), nullable=False)
    seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    approx_attempts_5s: Mapped[int] = mapped_column(Integer, nullable=False)
    manual_price_uzs: Mapped[int] = mapped_column(Integer, nullable=False)
    stars_price: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
    updated_by_admin_id: Mapped[int | None] = mapped_column(BigInteger)


class PackageChangeLog(Base):
    __tablename__ = "package_change_log"
    __table_args__ = (Index("ix_package_change_created", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    package_key: Mapped[str] = mapped_column(String(16), nullable=False)
    old_seconds: Mapped[int | None] = mapped_column(Integer)
    new_seconds: Mapped[int | None] = mapped_column(Integer)
    old_approx_attempts_5s: Mapped[int | None] = mapped_column(Integer)
    new_approx_attempts_5s: Mapped[int | None] = mapped_column(Integer)
    old_manual_price_uzs: Mapped[int | None] = mapped_column(Integer)
    new_manual_price_uzs: Mapped[int | None] = mapped_column(Integer)
    old_stars_price: Mapped[int | None] = mapped_column(Integer)
    new_stars_price: Mapped[int | None] = mapped_column(Integer)
    old_is_active: Mapped[bool | None] = mapped_column(Boolean)
    new_is_active: Mapped[bool | None] = mapped_column(Boolean)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class TranslationCache(Base):
    __tablename__ = "translation_cache"
    __table_args__ = (
        UniqueConstraint(
            "source_text_norm",
            "source_lang",
            "target_lang",
            name="uq_translation_cache_source",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_text_norm: Mapped[str] = mapped_column(String(256), nullable=False)
    source_lang: Mapped[str] = mapped_column(String(8), nullable=False)
    target_lang: Mapped[str] = mapped_column(String(8), nullable=False)
    translated_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class AppSetting(Base):
    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"
    __table_args__ = (Index("ix_admin_audit_created_at", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)
    target_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class TrainingSession(Base):
    __tablename__ = "training_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True)
    current_word_id: Mapped[int | None] = mapped_column(ForeignKey("words.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
