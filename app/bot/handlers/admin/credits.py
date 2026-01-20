from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.admin.common import ensure_admin_callback, ensure_admin_message, parse_int
from app.bot.handlers.admin.states import AdminStates
from app.bot.keyboards.admin.credits import admin_credits_menu_kb
from app.db.repo.admin import log_admin_action
from app.db.repo.credits import CreditError, add_topup
from app.db.repo.users import get_or_create_user, get_user_by_telegram_id
from app.db.session import AsyncSessionLocal
from app.services.i18n import t

router = Router()

_MAX_TOPUP_SECONDS = 1_000_000


@router.callback_query(F.data == "admin:credits")
async def admin_credits_menu(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    await state.set_state(AdminStates.menu)
    await callback.message.edit_text(t("admin_credits.menu"), reply_markup=admin_credits_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "admin:credits:add_id")
async def admin_credits_add_id(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    await state.set_state(AdminStates.credits_add_id)
    await callback.message.edit_text(t("admin_credits.prompt_id"))
    await callback.answer()


@router.message(AdminStates.credits_add_id)
async def admin_credits_add_id_value(message: Message, state: FSMContext) -> None:
    if not await ensure_admin_message(message):
        return
    telegram_id = parse_int(message.text or "")
    if not telegram_id:
        await message.answer(t("admin_credits.invalid_id"))
        return
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
    if not user:
        await message.answer(t("admin_credits.user_not_found"))
        return
    await state.update_data(credits_target_user_id=user.id, credits_target_telegram_id=telegram_id)
    await state.set_state(AdminStates.credits_add_seconds)
    await message.answer(t("admin_credits.prompt_seconds"))


@router.message(AdminStates.credits_add_seconds)
async def admin_credits_add_seconds(message: Message, state: FSMContext) -> None:
    if not await ensure_admin_message(message):
        return
    seconds = parse_int(message.text or "")
    if not seconds or seconds <= 0:
        await message.answer(t("admin_credits.invalid_seconds"))
        return
    if seconds > _MAX_TOPUP_SECONDS:
        await message.answer(t("admin_credits.too_large"))
        return
    data = await state.get_data()
    user_id = data.get("credits_target_user_id")
    telegram_id = data.get("credits_target_telegram_id")
    if not user_id or not telegram_id:
        await message.answer(t("admin_credits.user_not_selected"))
        return
    async with AsyncSessionLocal() as session:
        try:
            await add_topup(session, int(user_id), seconds, message.from_user.id, reason="admin_add")
            await log_admin_action(
                session, message.from_user.id, "credits_add", "user", str(user_id)
            )
        except CreditError as exc:
            await message.answer(exc.user_message or t("admin_credits.add_error"))
            return
    await message.answer(t("admin_credits.added"))
    try:
        await message.bot.send_message(int(telegram_id), t("admin_credits.notify_user", seconds=seconds))
    except Exception:
        pass
    await state.set_state(AdminStates.menu)


@router.callback_query(F.data == "admin:credits:forward")
async def admin_credits_forward(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    await state.set_state(AdminStates.menu)
    await callback.message.edit_text(
        t("admin_credits.forward_instructions")
    )
    await callback.answer()


@router.message(F.forward_from)
async def admin_credits_forward_message(message: Message, state: FSMContext) -> None:
    if not await ensure_admin_message(message):
        return
    forward_user = message.forward_from
    if not forward_user:
        return
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, forward_user.id, forward_user.username)
    await state.update_data(
        credits_target_user_id=user.id,
        credits_target_telegram_id=forward_user.id,
    )
    await state.set_state(AdminStates.credits_forward_seconds)
    await message.answer(t("admin_credits.prompt_seconds"))


@router.message(F.forward_sender_name)
async def admin_credits_forward_missing_id(message: Message) -> None:
    if not await ensure_admin_message(message):
        return
    await message.answer(t("admin_credits.forward_missing"))


@router.message(AdminStates.credits_forward_seconds)
async def admin_credits_forward_seconds(message: Message, state: FSMContext) -> None:
    if not await ensure_admin_message(message):
        return
    seconds = parse_int(message.text or "")
    if not seconds or seconds <= 0:
        await message.answer(t("admin_credits.invalid_seconds"))
        return
    if seconds > _MAX_TOPUP_SECONDS:
        await message.answer(t("admin_credits.too_large"))
        return
    data = await state.get_data()
    user_id = data.get("credits_target_user_id")
    telegram_id = data.get("credits_target_telegram_id")
    if not user_id or not telegram_id:
        await message.answer(t("admin_credits.user_not_selected"))
        return
    async with AsyncSessionLocal() as session:
        try:
            await add_topup(
                session, int(user_id), seconds, message.from_user.id, reason="admin_forward"
            )
            await log_admin_action(
                session, message.from_user.id, "credits_add", "user", str(user_id)
            )
        except CreditError as exc:
            await message.answer(exc.user_message or t("admin_credits.add_error"))
            return
    await message.answer(t("admin_credits.added"))
    try:
        await message.bot.send_message(int(telegram_id), t("admin_credits.notify_user", seconds=seconds))
    except Exception:
        pass
    await state.set_state(AdminStates.menu)


@router.message(F.text.startswith("/addcredit"))
async def admin_addcredit_command(message: Message, state: FSMContext) -> None:
    if not await ensure_admin_message(message):
        return
    parts = (message.text or "").split()
    if len(parts) < 3:
        await message.answer(t("admin_credits.command_usage"))
        return
    telegram_id = parse_int(parts[1])
    seconds = parse_int(parts[2])
    reason = " ".join(parts[3:]).strip() if len(parts) > 3 else None
    if not telegram_id or not seconds or seconds <= 0:
        await message.answer(t("admin_credits.invalid_command"))
        return
    if seconds > _MAX_TOPUP_SECONDS:
        await message.answer(t("admin_credits.too_large"))
        return
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, telegram_id)
        if not user:
            await message.answer(t("admin_credits.user_not_found"))
            return
        try:
            await add_topup(session, user.id, seconds, message.from_user.id, reason=reason or "admin_command")
            await log_admin_action(
                session, message.from_user.id, "credits_add", "user", str(user.id)
            )
        except CreditError as exc:
            await message.answer(exc.user_message or t("admin_credits.add_error"))
            return
    await message.answer(t("admin_credits.added"))
    try:
        await message.bot.send_message(int(telegram_id), t("admin_credits.notify_user", seconds=seconds))
    except Exception:
        pass
    await state.set_state(AdminStates.menu)
