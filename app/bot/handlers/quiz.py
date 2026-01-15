from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.exceptions import TelegramBadRequest

from app.bot.keyboards.main import main_menu_kb
from app.config import settings
from app.bot.keyboards.quiz import quiz_options_kb
from app.db.repo.srs import apply_review, get_due_words
from app.db.repo.admin import finish_quiz_session, log_quiz_session
from app.db.repo.user_settings import get_or_create_user_settings
from app.db.repo.users import get_or_create_user, get_user_by_telegram_id
from app.db.models import User, Word
from app.db.repo.words import get_words_by_user
from app.db.session import AsyncSessionLocal
from app.services.feature_flags import is_feature_enabled
from app.services.quiz import build_quiz_questions

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


async def _edit_or_send(
    message: Message,
    state: FSMContext,
    text: str,
    reply_markup=None,
    parse_mode: str | None = None,
) -> None:
    data = await state.get_data()
    message_id = data.get("quiz_message_id")
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
    await state.update_data(quiz_message_id=sent.message_id)


async def _send_next_question(
    message: Message, state: FSMContext, prefix: str | None = None
) -> None:
    data = await state.get_data()
    questions = data.get("questions", [])
    index = data.get("index", 0)
    if index >= len(questions):
        text = _quiz_result_text(data.get("correct", 0), data.get("wrong", 0))
        user_db_id = data.get("user_id")
        session_id = data.get("quiz_session_id")
        streak = 0
        is_admin = False
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_db_id) if user_db_id else None
            if user:
                streak = user.current_streak
                is_admin = user.telegram_id in settings.admin_user_ids
            if session_id:
                correct = data.get("correct", 0)
                wrong = data.get("wrong", 0)
                total = correct + wrong
                accuracy = int((correct / total) * 100) if total else 0
                await finish_quiz_session(session, session_id, total, correct, wrong, accuracy)
        await _edit_or_send(message, state, text, reply_markup=None)
        await message.answer(
            "Bosh menyu",
            reply_markup=main_menu_kb(is_admin=is_admin, streak=streak),
        )
        await state.clear()
        return

    question = questions[index]
    text = _quiz_question_text(
        str(question["translation"]), index + 1, len(questions)
    )
    if prefix:
        text = f"{prefix}\n\n{text}"
    await _edit_or_send(message, state, text, reply_markup=quiz_options_kb(question["options"]))


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
        if not await is_feature_enabled(session, "quiz"):
            await message.answer("🛑 Hozircha quiz o‘chirilgan.")
            return
        user = await get_user_by_telegram_id(session, user_id)
        if not user:
            await message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
            return
        all_words = await get_words_by_user(session, user.id)
        if len(all_words) < 4:
            await message.answer(
                "🙂 Quiz uchun kamida 4 ta so‘z kerak. Keling, avval so‘z qo‘shamiz!",
                reply_markup=main_menu_kb(
                    is_admin=message.from_user.id in settings.admin_user_ids,
                    streak=user.current_streak,
                ),
            )
            return
        user_settings = await get_or_create_user_settings(session, user)
        due_words = await get_due_words(
            session, user.id, user_settings.quiz_words_per_session
        )
        questions = build_quiz_questions(
            all_words, due_words, max_questions=user_settings.quiz_words_per_session
        )
        quiz_session_id = await log_quiz_session(session, user.id)

    await state.set_state(QuizStates.in_quiz)
    await state.update_data(
        questions=questions,
        index=0,
        correct=0,
        wrong=0,
        user_id=user.id,
        quiz_session_id=quiz_session_id,
    )
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
        word = await session.get(Word, correct_id)
        if not word:
            await _edit_or_send(
                callback.message,
                state,
                "⚠️ Karta topilmadi. Qaytadan urinib ko‘ring 🙂",
            )
            await state.clear()
            return
        if selected_id == correct_id:
            await apply_review(session, word, 4)
            feedback = "✅ To‘g‘ri! Zo‘r ketayapsiz 💪"
            await state.update_data(correct=data.get("correct", 0) + 1)
        else:
            await apply_review(session, word, 0)
            feedback = f"❌ Xato. To‘g‘ri javob: {question['word']} — {question['translation']}"
            await state.update_data(wrong=data.get("wrong", 0) + 1)

    await state.update_data(index=index + 1)
    await _send_next_question(callback.message, state, prefix=feedback)
    await callback.answer()


@router.callback_query(F.data == "quiz:exit")
async def quiz_exit(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    quiz_message_id = data.get("quiz_message_id")
    correct = data.get("correct", 0)
    wrong = data.get("wrong", 0)
    session_id = data.get("quiz_session_id")
    await state.clear()
    if quiz_message_id:
        try:
            await callback.message.bot.delete_message(
                chat_id=callback.message.chat.id,
                message_id=quiz_message_id,
            )
        except TelegramBadRequest:
            pass
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        streak = user.current_streak
        if session_id:
            total = correct + wrong
            accuracy = int((correct / total) * 100) if total else 0
            await finish_quiz_session(session, session_id, total, correct, wrong, accuracy)
    await callback.message.answer(
        f"🚪 Quiz to‘xtatildi.\n\n{_quiz_result_text(correct, wrong)}",
        reply_markup=main_menu_kb(
            is_admin=callback.from_user.id in settings.admin_user_ids, streak=streak
        ),
    )
    await callback.answer()
