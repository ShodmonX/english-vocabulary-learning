from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.practice import practice_quick_rate_kb, practice_quick_step_kb
from app.bot.handlers.practice.common import (
    apply_rating,
    edit_or_send,
    pick_review,
    update_current_review,
)
from app.bot.handlers.practice.states import PracticeStates
from app.bot.handlers.practice.summary import show_summary

router = Router()


def _quick_word_text(idx: int, total: int, word: str) -> str:
    return f"🟦 {idx}/{total}\n👉 *{word}*"


def _quick_reveal_text(word: str, translation: str, example: str | None) -> str:
    text = f"🟩 *{word}*\n➜ {translation}"
    if example:
        text += f"\n💬 {example}"
    return text


async def _advance(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    ids = data.get("word_ids", [])
    idx = data.get("idx", 0)
    if idx >= len(ids):
        await show_summary(callback.message, state)
        await callback.answer()
        return
    next_idx = idx + 1
    await state.update_data(idx=next_idx)
    if next_idx >= len(ids):
        await show_summary(callback.message, state)
        await callback.answer()
        return
    word = pick_review(data.get("items", []), next_idx)
    if not word:
        await callback.answer()
        return
    await update_current_review(callback.from_user.id, word.id)
    await state.set_state(PracticeStates.quick_word)
    await edit_or_send(
        callback.message,
        state,
        _quick_word_text(next_idx + 1, len(ids), word.word),
        reply_markup=practice_quick_step_kb(),
    )
    await callback.answer()


@router.callback_query(PracticeStates.quick_word, F.data == "practice:quick:show")
async def quick_show(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    idx = data.get("idx", 0)
    word = pick_review(data.get("items", []), idx)
    if not word:
        await state.set_state(PracticeStates.done)
        await callback.answer()
        return
    await state.set_state(PracticeStates.quick_reveal)
    await edit_or_send(
        callback.message,
        state,
        _quick_reveal_text(word.word, word.translation, word.example),
        reply_markup=practice_quick_rate_kb(),
    )
    await callback.answer()


@router.callback_query(PracticeStates.quick_word, F.data == "practice:quick:skip")
async def quick_skip(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    idx = data.get("idx", 0)
    word = pick_review(data.get("items", []), idx)
    if word:
        await apply_rating(word.id, 0)
        stats = data.get("stats", {"again": 0, "hard": 0, "good": 0, "easy": 0})
        stats["again"] += 1
        await state.update_data(stats=stats)
    await _advance(callback, state)


@router.callback_query(PracticeStates.quick_reveal, F.data.startswith("practice:rate:"))
async def quick_rate(callback: CallbackQuery, state: FSMContext) -> None:
    rating = callback.data.split(":")[-1]
    if rating not in {"again", "hard", "good", "easy"}:
        await callback.answer()
        return
    data = await state.get_data()
    idx = data.get("idx", 0)
    word = pick_review(data.get("items", []), idx)
    if word:
        q_map = {"again": 0, "hard": 3, "good": 4, "easy": 5}
        q = q_map[rating]
        await apply_rating(word.id, q)
        stats = data.get("stats", {"again": 0, "hard": 0, "good": 0, "easy": 0})
        stats[rating] += 1
        await state.update_data(stats=stats)
    await _advance(callback, state)
