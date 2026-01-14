from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.main import main_menu_kb
from app.bot.keyboards.quiz import quiz_options_kb
from app.db.repo.reviews import (
    get_due_reviews,
    get_review_by_word_id,
    log_review,
    update_review,
)
from app.db.repo.user_settings import get_or_create_user_settings
from app.db.repo.users import get_user_by_telegram_id
from app.db.repo.words import get_words_by_user
from app.db.session import AsyncSessionLocal
from app.services.quiz import build_quiz_questions
from app.services.srs import next_due_forgot, next_due_known

router = Router()


class QuizStates(StatesGroup):
    in_quiz = State()


def _quiz_question_text(translation: str, index: int, total: int) -> str:
    return (
        "🧩 Quiz savoli!\n"
        f"Tarjima: {translation}\n\n"
        f"Variantni tanlang 👇 ({index}/{total})"
    )


def _quiz_result_text(correct: int, wrong: int) -> str:
    total = correct + wrong
    accuracy = (correct / total * 100) if total else 0
    return (
        "🎉 Quiz yakunlandi!\n"
        f"✅ To‘g‘ri: {correct}\n"
        f"❌ Xato: {wrong}\n"
        f"📈 Aniqlik: {accuracy:.0f}%"
    )


async def _send_next_question(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    questions = data.get("questions", [])
    index = data.get("index", 0)
    if index >= len(questions):
        text = _quiz_result_text(data.get("correct", 0), data.get("wrong", 0))
        await message.answer(text, reply_markup=main_menu_kb())
        await state.clear()
        return

    question = questions[index]
    text = _quiz_question_text(
        str(question["translation"]), index + 1, len(questions)
    )
    await message.answer(text, reply_markup=quiz_options_kb(question["options"]))


@router.callback_query(F.data == "menu:quiz")
async def start_quiz(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_reply_markup(reply_markup=None)
    await start_quiz_message(callback.message, callback.from_user.id, state)
    await callback.answer()


async def start_quiz_message(
    message: Message, user_id: int, state: FSMContext
) -> None:
    await state.clear()
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, user_id)
        if not user:
            await message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
            return
        all_words = await get_words_by_user(session, user.id)
        if len(all_words) < 4:
            await message.answer(
                "🙂 Quiz uchun kamida 4 ta so‘z kerak. Keling, avval so‘z qo‘shamiz!",
                reply_markup=main_menu_kb(),
            )
            return
        settings = await get_or_create_user_settings(session, user)
        due_reviews = await get_due_reviews(session, user.id)
        due_words = [review.word for review in due_reviews]
        questions = build_quiz_questions(
            all_words, due_words, max_questions=settings.quiz_words_per_session
        )

    await state.set_state(QuizStates.in_quiz)
    await state.update_data(questions=questions, index=0, correct=0, wrong=0)
    await _send_next_question(message, state)


@router.callback_query(F.data.startswith("quiz:answer:"))
async def quiz_answer(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    questions = data.get("questions", [])
    index = data.get("index", 0)
    if index >= len(questions):
        await callback.answer("🙂 Savollar tugagan.")
        await state.clear()
        return

    selected_id = int(callback.data.split(":")[-1])
    question = questions[index]
    correct_id = int(question["word_id"])

    async with AsyncSessionLocal() as session:
        review = await get_review_by_word_id(session, correct_id)
        if not review:
            await callback.message.answer("⚠️ Karta topilmadi. Qaytadan urinib ko‘ring 🙂")
            await state.clear()
            return

        if selected_id == correct_id:
            stage, ease, interval, due_at = next_due_known(
                review.stage, review.ease_factor, review.interval_days
            )
            await update_review(session, review, stage, ease, interval, due_at)
            await log_review(session, review.user_id, review.word_id, "known")
            await callback.message.answer("✅ To‘g‘ri! Zo‘r ketayapsiz 💪")
            await state.update_data(correct=data.get("correct", 0) + 1)
        else:
            stage, ease, interval, due_at = next_due_forgot(
                review.stage, review.ease_factor, review.interval_days
            )
            await update_review(session, review, stage, ease, interval, due_at)
            await log_review(session, review.user_id, review.word_id, "forgot")
            await callback.message.answer(
                f"❌ Xato. To‘g‘ri javob: {question['word']} — {question['translation']}"
            )
            await state.update_data(wrong=data.get("wrong", 0) + 1)

    await state.update_data(index=index + 1)
    await _send_next_question(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "quiz:exit")
async def quiz_exit(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("🚪 Quiz yopildi. Keyin davom etamiz 🙂", reply_markup=main_menu_kb())
    await callback.answer()
