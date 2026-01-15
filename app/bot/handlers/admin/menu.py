from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.handlers.admin.common import ensure_admin_callback
from app.bot.handlers.admin.states import AdminStates
from app.bot.keyboards.admin.main import admin_menu_kb

router = Router()


@router.callback_query(F.data == "admin:menu")
async def admin_menu(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    await state.set_state(AdminStates.menu)
    await callback.message.edit_text("🛠 ADMIN PANEL", reply_markup=admin_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "admin:exit")
async def admin_exit(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    await state.clear()
    await callback.message.edit_text("🚪 Admin paneldan chiqildi.")
    await callback.answer()
