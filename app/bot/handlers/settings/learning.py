from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.settings import learning_kb
from app.bot.handlers.settings.states import SettingsStates
from app.db.repo.user_settings import get_or_create_user_settings, update_user_settings
from app.db.repo.users import get_user_by_telegram_id
from app.db.session import AsyncSessionLocal

router = Router()


def _learning_text(settings) -> str:
    return (
        "🧠 O‘rganish\n"
        f"📚 Kunlik maqsad: {settings.learning_words_per_day}\n"
        "🔁 Takrorlash: SRS (default)"
    )


@router.callback_query(F.data == "settings:learning")
async def learning_menu(callback: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
            await state.clear()
            return
        settings = await get_or_create_user_settings(session, user)
    await state.set_state(SettingsStates.learning)
    await callback.message.edit_text(_learning_text(settings), reply_markup=learning_kb())
    await callback.answer()


@router.callback_query(F.data == "settings:learning:srs")
async def learning_srs_placeholder(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer("ℹ️ Takrorlash algoritmi hozircha standart (SRS).")
    await callback.answer()


@router.callback_query(F.data == "settings:learning:words_per_day")
async def learning_words_per_day(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SettingsStates.learning_words_per_day)
    await callback.message.answer("📚 Kunlik maqsadni kiriting (5..100):")
    await callback.answer()


@router.callback_query(F.data == "settings:daily_goal")
async def legacy_daily_goal(callback: CallbackQuery, state: FSMContext) -> None:
    await learning_words_per_day(callback, state)


@router.message(SettingsStates.learning_words_per_day)
async def save_learning_words_per_day(message: Message, state: FSMContext) -> None:
    try:
        value = int(message.text.strip())
    except ValueError:
        await message.answer("❗ Iltimos, to‘g‘ri qiymat kiriting.")
        return
    if value < 5 or value > 100:
        await message.answer("❗ 5..100 oralig‘ida kiriting.")
        return

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
            await state.clear()
            return
        settings = await get_or_create_user_settings(session, user)
        settings = await update_user_settings(
            session, settings.user_id, learning_words_per_day=value
        )

    await state.set_state(SettingsStates.learning)
    await message.answer("✅ Saqlandi")
    await message.answer(_learning_text(settings), reply_markup=learning_kb())


@router.callback_query(F.data == "settings:learning:reset")
async def learning_reset(callback: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
            await state.clear()
            return
        settings = await get_or_create_user_settings(session, user)
        settings = await update_user_settings(
            session, settings.user_id, learning_words_per_day=10
        )
    await state.set_state(SettingsStates.learning)
    await callback.message.edit_text(_learning_text(settings), reply_markup=learning_kb())
    await callback.message.answer("✅ Saqlandi")
    await callback.answer()
