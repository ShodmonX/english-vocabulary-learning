from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.settings import limits_kb
from app.bot.handlers.settings.states import SettingsStates
from app.db.repo.user_settings import get_or_create_user_settings, update_user_settings
from app.db.repo.users import get_user_by_telegram_id
from app.db.session import AsyncSessionLocal

router = Router()


def _limits_text(settings) -> str:
    limit_text = (
        "cheksiz"
        if settings.daily_pronunciation_limit == 0
        else str(settings.daily_pronunciation_limit)
    )
    status = "ON" if settings.daily_limit_enabled else "OFF"
    return (
        "⚡ Cheklovlar\n"
        f"⚡ Talaffuz limiti: {limit_text}\n"
        f"🔒 Limitlar: {status}"
    )


@router.callback_query(F.data == "settings:limits")
async def limits_menu(callback: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
            await state.clear()
            return
        settings = await get_or_create_user_settings(session, user)
    await state.set_state(SettingsStates.limits)
    await callback.message.edit_text(
        _limits_text(settings), reply_markup=limits_kb(settings.daily_limit_enabled)
    )
    await callback.answer()


@router.callback_query(F.data == "settings:limits:pronunciation")
async def limits_pronunciation(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SettingsStates.limits_pronunciation)
    await callback.message.answer("⚡ Kunlik talaffuz limitini kiriting (0..100):")
    await callback.answer()


@router.message(SettingsStates.limits_pronunciation)
async def save_limits_pronunciation(message: Message, state: FSMContext) -> None:
    try:
        value = int(message.text.strip())
    except ValueError:
        await message.answer("❗ Iltimos, to‘g‘ri qiymat kiriting.")
        return
    if value < 0 or value > 100:
        await message.answer("❗ 0..100 oralig‘ida kiriting.")
        return

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
            await state.clear()
            return
        settings = await get_or_create_user_settings(session, user)
        settings = await update_user_settings(
            session, settings.user_id, daily_pronunciation_limit=value
        )

    await state.set_state(SettingsStates.limits)
    await message.answer("✅ Saqlandi")
    await message.answer(
        _limits_text(settings), reply_markup=limits_kb(settings.daily_limit_enabled)
    )


@router.callback_query(F.data == "settings:limits:quiz")
async def limits_quiz_placeholder(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer("ℹ️ Quiz limitlari tez orada qo‘shiladi.")
    await callback.answer()


@router.callback_query(F.data == "settings:limits:toggle")
async def limits_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
            await state.clear()
            return
        settings = await get_or_create_user_settings(session, user)
        new_value = not settings.daily_limit_enabled
        settings = await update_user_settings(
            session, settings.user_id, daily_limit_enabled=new_value
        )
    await state.set_state(SettingsStates.limits)
    await callback.message.edit_text(
        _limits_text(settings), reply_markup=limits_kb(settings.daily_limit_enabled)
    )
    await callback.message.answer("✅ Saqlandi")
    await callback.answer()


@router.callback_query(F.data == "settings:limits:reset")
async def limits_reset(callback: CallbackQuery, state: FSMContext) -> None:
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
            daily_pronunciation_limit=10,
            daily_limit_enabled=True,
        )
    await state.set_state(SettingsStates.limits)
    await callback.message.edit_text(
        _limits_text(settings), reply_markup=limits_kb(settings.daily_limit_enabled)
    )
    await callback.message.answer("✅ Saqlandi")
    await callback.answer()
