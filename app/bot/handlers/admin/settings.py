from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.admin.common import ensure_main_admin_callback, ensure_main_admin_message, parse_int
from app.bot.handlers.admin.entry import open_admin_panel
from app.bot.handlers.admin.states import AdminStates
from app.bot.keyboards.admin.settings import admin_basic_limit_kb
from app.bot.keyboards.admin.users import admin_confirm_kb
from app.config import settings
from app.db.repo.app_settings import get_basic_monthly_seconds, set_basic_monthly_seconds
from app.db.session import AsyncSessionLocal
from app.services.i18n import t

router = Router()

MIN_LIMIT = 1
MAX_LIMIT = 100000


async def _current_limit() -> int:
    async with AsyncSessionLocal() as session:
        value = await get_basic_monthly_seconds(session)
    return value if value and value > 0 else settings.basic_monthly_seconds


@router.callback_query(F.data == "admin:basic_limit")
async def admin_basic_limit(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_main_admin_callback(callback):
        return
    await state.set_state(AdminStates.menu)
    value = await _current_limit()
    await callback.message.edit_text(
        t("admin_settings.basic_limit_body", value=value),
        reply_markup=admin_basic_limit_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:basic_limit:edit")
async def admin_basic_limit_edit(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_main_admin_callback(callback):
        return
    await state.set_state(AdminStates.basic_limit_edit)
    await callback.message.edit_text(t("admin_settings.basic_limit_prompt"))
    await callback.answer()


@router.message(AdminStates.basic_limit_edit)
async def admin_basic_limit_value(message: Message, state: FSMContext) -> None:
    if not await ensure_main_admin_message(message):
        return
    new_value = parse_int(message.text or "")
    if not new_value or not (MIN_LIMIT <= new_value <= MAX_LIMIT):
        await message.answer(t("admin_settings.basic_limit_invalid"))
        return
    old_value = await _current_limit()
    await state.update_data(basic_limit_new=new_value, basic_limit_old=old_value)
    await message.answer(
        t("admin_settings.basic_limit_confirm", old=old_value, new=new_value),
        reply_markup=admin_confirm_kb(
            "admin:basic_limit:confirm", "admin:basic_limit:cancel"
        ),
    )


@router.callback_query(F.data == "admin:basic_limit:confirm")
async def admin_basic_limit_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_main_admin_callback(callback):
        return
    data = await state.get_data()
    new_value = data.get("basic_limit_new")
    if not new_value:
        await callback.answer(t("admin_settings.basic_limit_invalid"), show_alert=True)
        return
    async with AsyncSessionLocal() as session:
        await set_basic_monthly_seconds(session, int(new_value), callback.from_user.id)
    settings.basic_monthly_seconds = int(new_value)
    await state.clear()
    await callback.message.answer(
        t("admin_settings.basic_limit_updated", new=new_value)
    )
    await open_admin_panel(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "admin:basic_limit:cancel")
async def admin_basic_limit_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_main_admin_callback(callback):
        return
    await state.clear()
    value = await _current_limit()
    await callback.message.edit_text(
        t("admin_settings.basic_limit_body", value=value),
        reply_markup=admin_basic_limit_kb(),
    )
    await callback.answer()
