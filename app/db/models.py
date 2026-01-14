from __future__ import annotations

from datetime import datetime, time

from sqlalchemy import (
    BigInteger,
    Boolean,
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
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.utcnow()


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    daily_goal: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    reminder_time: Mapped[time] = mapped_column(Time, default=time(20, 0), nullable=False)
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Tashkent")
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


class Word(Base):
    __tablename__ = "words"
    __table_args__ = (
        UniqueConstraint("user_id", "word", name="uq_words_user_word"),
        Index("ix_words_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    word: Mapped[str] = mapped_column(String(128), nullable=False)
    translation: Mapped[str] = mapped_column(String(256), nullable=False)
    example: Mapped[str | None] = mapped_column(Text)
    pos: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class PronunciationLog(Base):
    __tablename__ = "pronunciation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
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


class TrainingSession(Base):
    __tablename__ = "training_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True)
    current_review_id: Mapped[int | None] = mapped_column(ForeignKey("reviews.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
