from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.main import main_menu_kb
from app.bot.keyboards.settings import settings_main_kb
from app.bot.handlers.settings.states import SettingsStates
from app.db.repo.user_settings import get_or_create_user_settings
from app.db.repo.users import get_user_by_telegram_id
from app.db.session import AsyncSessionLocal

router = Router()


def _menu_text(settings) -> str:
    notifications = "ON" if settings.notifications_enabled else "OFF"
    auto_translation = "ON" if settings.auto_translation_suggest else "OFF"
    pronunciation = "ON" if settings.pronunciation_enabled else "OFF"
    return (
        "⚙️ Sozlamalar\n"
        f"📚 Kunlik maqsad: {settings.learning_words_per_day}\n"
        f"🧩 Quiz: {settings.quiz_words_per_session}\n"
        f"🗣 Talaffuz: {pronunciation}\n"
        f"🤖 Avto tarjima: {auto_translation}\n"
        f"🔔 Eslatmalar: {notifications}"
    )


async def open_settings_message(
    message: Message, user_id: int, state: FSMContext
) -> None:
    await state.clear()
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, user_id)
        if not user:
            await message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
            return
        settings = await get_or_create_user_settings(session, user)
    await state.set_state(SettingsStates.menu)
    await message.answer(_menu_text(settings), reply_markup=settings_main_kb())


@router.callback_query(F.data == "menu:settings")
async def open_settings(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_reply_markup(reply_markup=None)
    await open_settings_message(callback.message, callback.from_user.id, state)
    await callback.answer()


@router.callback_query(F.data == "settings:menu")
async def settings_menu(callback: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
            await state.clear()
            return
        settings = await get_or_create_user_settings(session, user)
    await state.set_state(SettingsStates.menu)
    await callback.message.edit_text(_menu_text(settings), reply_markup=settings_main_kb())
    await callback.answer()


@router.callback_query(F.data == "settings:back")
async def settings_back(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("⬅️ Bosh menyu")
    await callback.message.answer("Bosh menyu", reply_markup=main_menu_kb())
    await callback.answer()
