from __future__ import annotations

from datetime import time

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.main import main_menu_kb, settings_kb
from app.db.repo.users import get_user_by_telegram_id, update_daily_goal, update_reminder_time
from app.db.session import AsyncSessionLocal

router = Router()


class SettingsStates(StatesGroup):
    daily_goal = State()
    reminder_time = State()


@router.callback_query(F.data == "menu:settings")
async def open_settings(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("Sozlamalar:", reply_markup=settings_kb())
    await callback.answer()


@router.callback_query(F.data == "settings:back")
async def settings_back(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer("Bosh menyu", reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "settings:daily_goal")
async def settings_daily_goal(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SettingsStates.daily_goal)
    await callback.message.answer("Kunlik maqsadni kiriting (5..100):")
    await callback.answer()


@router.message(SettingsStates.daily_goal)
async def save_daily_goal(message: Message, state: FSMContext) -> None:
    try:
        value = int(message.text.strip())
    except ValueError:
        await message.answer("Noto‘g‘ri format. 5..100 oralig‘ida son kiriting.")
        return
    if value < 5 or value > 100:
        await message.answer("Noto‘g‘ri diapazon. 5..100 oralig‘ida kiriting.")
        return

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer("Avval /start buyrug‘ini bosing.")
            await state.clear()
            return
        await update_daily_goal(session, user.id, value)

    await message.answer("Kunlik maqsad yangilandi.", reply_markup=settings_kb())
    await state.clear()


@router.callback_query(F.data == "settings:reminder_time")
async def settings_reminder_time(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SettingsStates.reminder_time)
    await callback.message.answer("Eslatma vaqtini HH:MM formatida kiriting:")
    await callback.answer()


def _parse_time(value: str) -> time | None:
    parts = value.strip().split(":")
    if len(parts) != 2:
        return None
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        return None
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    return time(hour, minute)


@router.message(SettingsStates.reminder_time)
async def save_reminder_time(message: Message, state: FSMContext) -> None:
    parsed = _parse_time(message.text)
    if not parsed:
        await message.answer("Noto‘g‘ri format. Masalan: 20:00")
        return

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer("Avval /start buyrug‘ini bosing.")
            await state.clear()
            return
        await update_reminder_time(session, user.id, parsed)

    from app.main import reminder_service

    reminder_service.schedule_user(message.from_user.id, parsed, "Asia/Tashkent")

    await message.answer("Eslatma vaqti yangilandi.", reply_markup=settings_kb())
    await state.clear()
