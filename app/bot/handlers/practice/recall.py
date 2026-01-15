from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.practice import practice_quick_rate_kb, practice_recall_prompt_kb
from app.bot.handlers.practice.common import (
    apply_rating,
    edit_or_send,
    fuzzy_match,
    pick_review,
    update_current_review,
)
from app.bot.handlers.practice.states import PracticeStates
from app.bot.handlers.practice.summary import show_summary

router = Router()


def _recall_prompt_text(word: str) -> str:
    return f"🧠 Tarjimasini yozing:\n👉 *{word}*"


def _recall_result_text(word: str, translation: str, answer: str, is_close: bool) -> str:
    verdict = "✅ Yaqin/To‘g‘ri" if is_close else "❌ Noto‘g‘ri"
    return f"{verdict}\n🟩 *{word}*\n➜ {translation}\n🧩 Siz: {answer}"


async def _advance(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    ids = data.get("word_ids", [])
    idx = data.get("idx", 0)
    next_idx = idx + 1
    await state.update_data(idx=next_idx)
    if next_idx >= len(ids):
        await show_summary(message, state)
        return
    word = pick_review(data.get("items", []), next_idx)
    if not word:
        await show_summary(message, state)
        return
    await update_current_review(message.from_user.id, word.id)
    await state.set_state(PracticeStates.recall_await_answer)
    await edit_or_send(
        message,
        state,
        _recall_prompt_text(word.word),
        reply_markup=practice_recall_prompt_kb(),
    )


@router.message(PracticeStates.recall_await_answer)
async def recall_answer(message: Message, state: FSMContext) -> None:
    if not message.text:
        await message.answer("❗ Iltimos, javobni yozing.")
        return
    answer = message.text.strip()
    if not answer:
        await message.answer("❗ Iltimos, javobni yozing.")
        return
    data = await state.get_data()
    idx = data.get("idx", 0)
    word = pick_review(data.get("items", []), idx)
    if not word:
        await show_summary(message, state)
        return
    is_close = fuzzy_match(answer, word.translation)
    await state.set_state(PracticeStates.scoring)
    await edit_or_send(
        message,
        state,
        _recall_result_text(word.word, word.translation, answer, is_close),
        reply_markup=practice_quick_rate_kb(),
    )


@router.callback_query(PracticeStates.recall_await_answer, F.data == "practice:recall:skip")
async def recall_skip(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    idx = data.get("idx", 0)
    word = pick_review(data.get("items", []), idx)
    if word:
        await apply_rating(word.id, 0)
        stats = data.get("stats", {"again": 0, "hard": 0, "good": 0, "easy": 0})
        stats["again"] += 1
        await state.update_data(stats=stats)
    await _advance(callback.message, state)


@router.callback_query(PracticeStates.scoring, F.data.startswith("practice:rate:"))
async def recall_rate(callback: CallbackQuery, state: FSMContext) -> None:
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
    await _advance(callback.message, state)
