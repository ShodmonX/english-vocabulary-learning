from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.keyboards.settings import language_kb
from app.bot.handlers.settings.states import SettingsStates
from app.db.repo.user_settings import get_or_create_user_settings, update_user_settings
from app.db.repo.users import get_user_by_telegram_id
from app.db.session import AsyncSessionLocal

router = Router()


def _language_text(settings) -> str:
    auto_translation = "ON" if settings.auto_translation_suggest else "OFF"
    return (
        "🌍 Til & Tarjima\n"
        "🌍 Asosiy yo‘nalish: EN → UZ\n"
        f"🤖 Avto tarjima: {auto_translation}\n"
        f"🔄 Engine: {settings.translation_engine}"
    )


@router.callback_query(F.data == "settings:language")
async def language_menu(callback: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
            await state.clear()
            return
        settings = await get_or_create_user_settings(session, user)
    await state.set_state(SettingsStates.language)
    await callback.message.edit_text(
        _language_text(settings), reply_markup=language_kb(settings.auto_translation_suggest)
    )
    await callback.answer()


@router.callback_query(F.data == "settings:language:auto_toggle")
async def language_toggle_auto(callback: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
            await state.clear()
            return
        settings = await get_or_create_user_settings(session, user)
        new_value = not settings.auto_translation_suggest
        settings = await update_user_settings(
            session, settings.user_id, auto_translation_suggest=new_value
        )
    await state.set_state(SettingsStates.language)
    await callback.message.edit_text(
        _language_text(settings), reply_markup=language_kb(settings.auto_translation_suggest)
    )
    await callback.message.answer("✅ Saqlandi")
    await callback.answer()


@router.callback_query(F.data == "settings:language:engine")
async def language_engine(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer("ℹ️ Hozirda Google Translate ishlatilmoqda.")
    await callback.answer()


@router.callback_query(F.data == "settings:language:base_lang")
async def language_base(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer("ℹ️ Hozircha faqat EN → UZ mavjud.")
    await callback.answer()


@router.callback_query(F.data == "settings:language:reset")
async def language_reset(callback: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
            await state.clear()
            return
        settings = await get_or_create_user_settings(session, user)
        settings = await update_user_settings(
            session,
            settings.user_id,
            translation_enabled=True,
            translation_engine="google",
            auto_translation_suggest=True,
        )
    await state.set_state(SettingsStates.language)
    await callback.message.edit_text(
        _language_text(settings), reply_markup=language_kb(settings.auto_translation_suggest)
    )
    await callback.message.answer("✅ Saqlandi")
    await callback.answer()
