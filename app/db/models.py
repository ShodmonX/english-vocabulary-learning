from __future__ import annotations

from datetime import datetime, time

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, Time, UniqueConstraint
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
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Tashkent")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    words: Mapped[list[Word]] = relationship("Word", back_populates="user")


class Word(Base):
    __tablename__ = "words"
    __table_args__ = (UniqueConstraint("user_id", "word", name="uq_words_user_word"),)

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

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    word_id: Mapped[int] = mapped_column(ForeignKey("words.id"), nullable=False, unique=True)
    stage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
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
