from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.admin.common import ensure_admin_callback, ensure_admin_message, parse_int
from app.bot.handlers.admin.states import AdminStates
from app.bot.keyboards.admin.users import admin_user_actions_kb, admin_users_menu_kb
from app.db.repo.admin import get_user_summary, log_admin_action, set_user_blocked
from app.db.session import AsyncSessionLocal
from app.config import settings
from app.services.i18n import t
from zoneinfo import ZoneInfo
from datetime import timezone as dt_timezone

router = Router()


@router.callback_query(F.data == "admin:users")
async def admin_users_menu(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    await state.set_state(AdminStates.menu)
    await callback.message.edit_text(t("admin_users.menu"), reply_markup=admin_users_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "admin:users:search")
async def admin_users_search_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    await state.set_state(AdminStates.users_search)
    await callback.message.edit_text(t("admin_users.prompt_id"))
    await callback.answer()


@router.message(AdminStates.users_search)
async def admin_users_search(message: Message, state: FSMContext) -> None:
    if not await ensure_admin_message(message):
        return
    telegram_id = parse_int(message.text or "")
    if not telegram_id:
        await message.answer(t("admin_users.invalid_id"))
        return
    async with AsyncSessionLocal() as session:
        summary = await get_user_summary(session, telegram_id)
    if not summary:
        await message.answer(t("admin_users.user_not_found"))
        return
    await state.update_data(admin_target_user_id=summary["id"], admin_target_telegram_id=telegram_id)
    last_activity = (
        summary["last_activity"].strftime("%Y-%m-%d %H:%M")
        if summary["last_activity"]
        else t("common.none")
    )
    if summary["next_basic_refill_at"]:
        tz = ZoneInfo(settings.timezone)
        next_refill = (
            summary["next_basic_refill_at"]
            .replace(tzinfo=dt_timezone.utc)
            .astimezone(tz)
            .strftime("%Y-%m-%d %H:%M")
        )
    else:
        next_refill = t("common.none")
    username = (
        f"@{summary['username']}" if summary.get("username") else t("common.none")
    )
    text = t(
        "admin_users.summary",
        telegram_id=summary["telegram_id"],
        username=username,
        words=summary["words_count"],
        due=summary["due_count"],
        last_activity=last_activity,
        blocked=t("admin_users.blocked_yes") if summary["is_blocked"] else t("admin_users.blocked_no"),
        basic_remaining=summary["basic_remaining_seconds"],
        topup_remaining=summary["topup_remaining_seconds"],
        basic_used=summary["basic_used_seconds"],
        basic_limit=summary["basic_monthly_seconds"],
        next_refill=next_refill,
    )
    await message.answer(text, reply_markup=admin_user_actions_kb(summary["is_blocked"]))
    await state.set_state(AdminStates.menu)


@router.callback_query(F.data.in_(["admin:users:block", "admin:users:unblock"]))
async def admin_users_block_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    data = await state.get_data()
    user_id = data.get("admin_target_user_id")
    if not user_id:
        await callback.answer(t("admin_users.user_not_selected"))
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
    await callback.message.answer(t("admin_users.saved"))
    await callback.answer()
