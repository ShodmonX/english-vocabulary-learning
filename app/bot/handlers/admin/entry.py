from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.handlers.admin.common import ensure_admin_message, is_main_admin
from app.bot.keyboards.admin.main import admin_menu_kb
from app.bot.handlers.admin.states import AdminStates
from app.services.i18n import t

router = Router()


async def open_admin_panel(message: Message, state: FSMContext) -> None:
    await state.set_state(AdminStates.menu)
    await message.answer(
        t("admin.menu_title"),
        reply_markup=admin_menu_kb(is_owner=is_main_admin(message.from_user.id)),
    )


@router.message(Command("admin"))
async def admin_entry(message: Message, state: FSMContext) -> None:
    if not await ensure_admin_message(message):
        return
    await open_admin_panel(message, state)
