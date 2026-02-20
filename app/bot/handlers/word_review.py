from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.word_review import word_review_kb
from app.db.repo.users import get_user_by_telegram_id
from app.db.repo.words import count_words, list_recent_words
from app.db.session import AsyncSessionLocal
from app.services.i18n import t

router = Router()


def _review_text(word, *, position: int, total: int) -> str:
    lines = [
        t("word_review.header", position=position, total=total),
        t("word_review.word_line", word=word.word),
        t("word_review.translation_line", translation=word.translation),
    ]
    if word.example:
        lines.append(t("word_review.example_line", example=word.example))
    return "\n".join(lines)


async def _load_review_word(telegram_user_id: int, offset: int):
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, telegram_user_id)
        if not user:
            return None, None, 0, 0
        total = await count_words(session, user.id)
        if total <= 0:
            return user, None, 0, 0
        safe_offset = max(0, min(offset, total - 1))
        words = await list_recent_words(session, user.id, limit=1, offset=safe_offset)
    if not words:
        return user, None, safe_offset, total
    return user, words[0], safe_offset, total


async def _edit_message_safe(message: Message, *, text: str, reply_markup=None) -> None:
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc):
            return
        raise


async def _render_review_message(
    message: Message,
    *,
    telegram_user_id: int,
    offset: int,
    edit: bool,
) -> None:
    user, word, safe_offset, total = await _load_review_word(telegram_user_id, offset)
    if not user:
        if edit:
            await _edit_message_safe(message, text=t("common.start_required"))
        else:
            await message.answer(t("common.start_required"))
        return
    if not word:
        if edit:
            await _edit_message_safe(message, text=t("word_review.empty"))
        else:
            await message.answer(t("word_review.empty"))
        return

    text = _review_text(
        word,
        position=safe_offset + 1,
        total=total,
    )
    markup = word_review_kb(offset=safe_offset, total=total, word_id=word.id)
    if edit:
        await _edit_message_safe(message, text=text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)


async def open_word_review_message(message: Message, state: FSMContext) -> None:
    await state.clear()
    await _render_review_message(
        message,
        telegram_user_id=message.from_user.id,
        offset=0,
        edit=False,
    )


async def open_word_review_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _render_review_message(
        callback.message,
        telegram_user_id=callback.from_user.id,
        offset=0,
        edit=True,
    )


@router.callback_query(F.data.startswith("wr:nav:"))
async def word_review_nav(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    if len(parts) not in {3, 4}:
        await callback.answer()
        return
    try:
        offset = int(parts[2])
    except ValueError:
        await callback.answer()
        return
    await _render_review_message(
        callback.message,
        telegram_user_id=callback.from_user.id,
        offset=offset,
        edit=True,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("wr:toggle:"))
async def word_review_toggle_compat(callback: CallbackQuery) -> None:
    parts = callback.data.split(":")
    if len(parts) != 4:
        await callback.answer()
        return
    try:
        offset = int(parts[2])
    except ValueError:
        await callback.answer()
        return
    await _render_review_message(
        callback.message,
        telegram_user_id=callback.from_user.id,
        offset=offset,
        edit=True,
    )
    await callback.answer()


@router.callback_query(F.data == "wr:noop")
async def word_review_noop(callback: CallbackQuery) -> None:
    await callback.answer()
