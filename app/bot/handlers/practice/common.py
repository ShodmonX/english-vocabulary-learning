from __future__ import annotations

from typing import Iterable

from sqlalchemy import select

from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from rapidfuzz.fuzz import ratio

from app.db.models import Word
from app.db.repo.sessions import create_session, delete_session, get_session, update_session_word
from app.db.repo.srs import apply_review, get_due_words, get_new_words
from app.db.repo.user_settings import get_or_create_user_settings
from app.db.repo.users import get_or_create_user
from app.db.session import AsyncSessionLocal


SESSION_SIZE_DEFAULT = 10


def normalize(text: str) -> str:
    return " ".join(text.lower().split())


def fuzzy_match(a: str, b: str) -> bool:
    return ratio(normalize(a), normalize(b)) >= 75


def init_stats() -> dict[str, int]:
    return {"again": 0, "hard": 0, "good": 0, "easy": 0}


async def edit_or_send(
    message: Message, state: FSMContext, text: str, reply_markup=None, parse_mode: str | None = "Markdown"
) -> None:
    data = await state.get_data()
    message_id = data.get("practice_message_id")
    if message_id:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
            return
        except TelegramBadRequest:
            pass
    sent = await message.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
    await state.update_data(practice_message_id=sent.message_id)


async def ensure_session(user_id: int) -> tuple[int, bool]:
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, user_id)
        settings = await get_or_create_user_settings(session, user)
        existed = await get_session(session, user.id)
        if existed:
            await delete_session(session, user.id)
        created = await create_session(session, user.id)
        if not created:
            await delete_session(session, user.id)
            await create_session(session, user.id)
        limit = settings.learning_words_per_day or SESSION_SIZE_DEFAULT
        if limit < 1:
            limit = SESSION_SIZE_DEFAULT
        return user.id, limit


async def build_due_items(telegram_id: int, limit: int) -> list[Word]:
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, telegram_id)
        due_words = await get_due_words(session, user.id, limit)
        return due_words


async def build_new_items(telegram_id: int, limit: int) -> list[Word]:
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, telegram_id)
        new_words = await get_new_words(session, user.id, limit)
        return new_words


async def update_current_review(user_id: int, word_id: int) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, user_id)
        await update_session_word(session, user.id, word_id)


async def apply_rating(word_id: int, q: int) -> None:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Word).where(Word.id == word_id))
        word = result.scalar_one_or_none()
        if not word:
            return
        await apply_review(session, word, q)


def pick_review(items: list[Word], idx: int) -> Word | None:
    if idx < 0 or idx >= len(items):
        return None
    return items[idx]


def as_list(value: Iterable[int] | None) -> list[int]:
    return list(value) if value else []
