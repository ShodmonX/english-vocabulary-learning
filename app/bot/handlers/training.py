from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery

from app.bot.keyboards.main import main_menu_kb, training_kb
from app.db.repo.reviews import get_due_reviews, get_review_by_id, log_review, update_review
from app.db.repo.users import get_user_by_telegram_id
from app.db.session import AsyncSessionLocal
from app.services.srs import next_due_forgot, next_due_known, next_due_skip

router = Router()


class TrainingStates(StatesGroup):
    in_session = State()


def _card_text(word: str) -> str:
    return f"So‘z: {word}"


def _meaning_text(translation: str, example: str | None, pos: str | None) -> str:
    text = f"Tarjima: {translation}"
    if example:
        text += f"\nMisol: {example}"
    if pos:
        text += f"\nSo‘z turkumi: {pos}"
    return text


async def send_next_card(callback: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer("Avval /start buyrug‘ini bosing.")
            await state.clear()
            return
        due_reviews = await get_due_reviews(session, user.id)
        if not due_reviews:
            await callback.message.answer("Hozircha mashq uchun so‘z yo‘q.", reply_markup=main_menu_kb())
            await state.clear()
            return
        review = due_reviews[0]
        await state.set_state(TrainingStates.in_session)
        await state.update_data(review_id=review.id, meaning_shown=False)
        await callback.message.answer(_card_text(review.word.word), reply_markup=training_kb())


@router.callback_query(F.data == "menu:training")
async def start_training(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await send_next_card(callback, state)
    await callback.answer()


@router.callback_query(F.data == "train:show")
async def show_meaning(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    review_id = data.get("review_id")
    if not review_id:
        await callback.answer("Aktiv karta yo‘q.")
        return

    async with AsyncSessionLocal() as session:
        review = await get_review_by_id(session, review_id)
        if not review:
            await callback.message.answer("Karta topilmadi.")
            await state.clear()
            return
        text = _meaning_text(
            review.word.translation, review.word.example, review.word.pos
        )
        await state.update_data(meaning_shown=True)
        await callback.message.answer(text, reply_markup=training_kb(show_meaning=True))
        await callback.answer()


async def _handle_answer(callback: CallbackQuery, state: FSMContext, action: str) -> None:
    data = await state.get_data()
    review_id = data.get("review_id")
    if not review_id:
        await callback.answer("Aktiv karta yo‘q.")
        return

    async with AsyncSessionLocal() as session:
        review = await get_review_by_id(session, review_id)
        if not review:
            await callback.message.answer("Karta topilmadi.")
            await state.clear()
            return

        if action == "known":
            stage, due_at = next_due_known(review.stage)
        elif action == "forgot":
            stage, due_at = next_due_forgot(review.stage)
        else:
            stage, due_at = next_due_skip(review.stage)

        await update_review(session, review, stage, due_at)
        await log_review(session, review.user_id, review.word_id, action)

    await send_next_card(callback, state)
    await callback.answer()


@router.callback_query(F.data == "train:knew")
async def train_knew(callback: CallbackQuery, state: FSMContext) -> None:
    await _handle_answer(callback, state, "known")


@router.callback_query(F.data == "train:forgot")
async def train_forgot(callback: CallbackQuery, state: FSMContext) -> None:
    await _handle_answer(callback, state, "forgot")


@router.callback_query(F.data == "train:skip")
async def train_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await _handle_answer(callback, state, "skip")


@router.callback_query(F.data == "train:exit")
async def train_exit(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("Mashq tugatildi.", reply_markup=main_menu_kb())
    await callback.answer()
