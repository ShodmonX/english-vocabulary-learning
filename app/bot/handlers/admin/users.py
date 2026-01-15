from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.admin.common import ensure_admin_callback, ensure_admin_message, parse_int
from app.bot.handlers.admin.states import AdminStates
from app.bot.keyboards.admin.users import admin_user_actions_kb, admin_users_menu_kb
from app.db.repo.admin import get_user_summary, log_admin_action, set_user_blocked
from app.db.session import AsyncSessionLocal

router = Router()


@router.callback_query(F.data == "admin:users")
async def admin_users_menu(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    await state.set_state(AdminStates.menu)
    await callback.message.edit_text("👥 Foydalanuvchilar bo‘limi:", reply_markup=admin_users_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "admin:users:search")
async def admin_users_search_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    await state.set_state(AdminStates.users_search)
    await callback.message.edit_text("🔍 Telegram ID kiriting:")
    await callback.answer()


@router.message(AdminStates.users_search)
async def admin_users_search(message: Message, state: FSMContext) -> None:
    if not await ensure_admin_message(message):
        return
    telegram_id = parse_int(message.text or "")
    if not telegram_id:
        await message.answer("❗ Telegram ID raqam bo‘lishi kerak.")
        return
    async with AsyncSessionLocal() as session:
        summary = await get_user_summary(session, telegram_id)
    if not summary:
        await message.answer("🫤 User topilmadi.")
        return
    await state.update_data(admin_target_user_id=summary["id"], admin_target_telegram_id=telegram_id)
    last_activity = summary["last_activity"].strftime("%Y-%m-%d %H:%M") if summary["last_activity"] else "—"
    text = (
        "👤 User summary:\n"
        f"telegram_id: {summary['telegram_id']}\n"
        f"username: {summary['username'] or '—'}\n"
        f"so‘zlar: {summary['words_count']}\n"
        f"due: {summary['due_count']}\n"
        f"oxirgi activity: {last_activity}\n"
        f"bloklangan: {'ha' if summary['is_blocked'] else 'yo‘q'}"
    )
    await message.answer(text, reply_markup=admin_user_actions_kb(summary["is_blocked"]))


@router.callback_query(F.data.in_(["admin:users:block", "admin:users:unblock"]))
async def admin_users_block_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    data = await state.get_data()
    user_id = data.get("admin_target_user_id")
    if not user_id:
        await callback.answer("⚠️ User tanlanmagan.")
        return
    block = callback.data == "admin:users:block"
    async with AsyncSessionLocal() as session:
        await set_user_blocked(session, int(user_id), block)
        await log_admin_action(
            session,
            callback.from_user.id,
            "user_block" if block else "user_unblock",
            "user",
            str(user_id),
        )
    await callback.message.answer("✅ Saqlandi.")
    await callback.answer()
