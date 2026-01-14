from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.keyboards.settings import advanced_kb, advanced_reset_confirm_kb
from app.bot.handlers.settings.states import SettingsStates
from app.db.repo.user_settings import get_or_create_user_settings, reset_user_settings
from app.db.repo.users import get_user_by_telegram_id
from app.db.session import AsyncSessionLocal

router = Router()


@router.callback_query(F.data == "settings:advanced")
async def advanced_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SettingsStates.advanced)
    await callback.message.edit_text("🛠 Texnik sozlamalar", reply_markup=advanced_kb())
    await callback.answer()


@router.callback_query(F.data == "settings:advanced:reset")
async def advanced_reset_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "Rostdan ham barcha sozlamalarni defaultga qaytarmoqchimisiz?",
        reply_markup=advanced_reset_confirm_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "settings:advanced:reset_confirm")
async def advanced_reset_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
            await state.clear()
            return
        await get_or_create_user_settings(session, user)
        await reset_user_settings(session, user)

    from app.main import reminder_service

    reminder_service.remove_user(callback.from_user.id)
    await callback.message.edit_text("✅ Sozlamalar defaultga qaytarildi.")
    await callback.message.answer("🛠 Texnik sozlamalar", reply_markup=advanced_kb())
    await callback.answer()


@router.callback_query(F.data == "settings:advanced:clear_sessions")
async def advanced_clear_sessions(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("🧹 Sessionlar tozalandi. Boshidan boshlaymiz 🙂")
    await callback.answer()
