from __future__ import annotations

from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.admin.common import (
    ensure_main_admin_callback,
    ensure_main_admin_message,
    get_main_admin_id,
    parse_int,
)
from app.bot.handlers.admin.states import AdminStates
from app.bot.keyboards.admin.admins import (
    admin_admin_add_confirm_kb,
    admin_admin_detail_kb,
    admin_admin_remove_confirm_kb,
    admin_admins_add_method_kb,
    admin_admins_cancel_kb,
    admin_admins_list_kb,
    admin_admins_menu_kb,
)
from app.config import settings
from app.db.models import BotAdmin, User
from app.db.repo.admin import get_user_by_telegram_id, get_user_summary
from app.db.repo.bot_admins import get_admin, list_admins, remove_admin, upsert_admin
from app.db.session import AsyncSessionLocal
from app.services.i18n import t

router = Router()


def _format_dt(value: datetime | None) -> str:
    if not value:
        return "—"
    return value.strftime("%Y-%m-%d %H:%M")


def _display_name(admin: BotAdmin) -> str:
    return admin.first_name or admin.username or str(admin.tg_user_id)


def _extract_forward_user(message: Message):
    if message.forward_from:
        return message.forward_from
    origin = getattr(message, "forward_origin", None)
    if origin and getattr(origin, "sender_user", None):
        return origin.sender_user
    return None


async def _render_preview(
    message: Message,
    state: FSMContext,
    *,
    target_id: int,
    first_name: str,
    username: str | None,
) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, target_id)
        if not user:
            await message.answer(t("admin_admins.user_not_found"))
            return
        summary = await get_user_summary(session, target_id)
        created_at = user.created_at if isinstance(user, User) else None
        if user.username and (not first_name or first_name == str(target_id)):
            first_name = user.username
        if not username:
            username = user.username
    words_count = summary.get("words_count", 0) if summary else 0
    due_count = summary.get("due_count", 0) if summary else 0
    last_activity = summary.get("last_activity") if summary else None
    await state.update_data(
        pending_admin_id=target_id,
        pending_admin_name=first_name,
        pending_admin_username=username,
    )
    await message.answer(
        t(
            "admin_admins.preview",
            name=first_name,
            username=username or "—",
            tg_user_id=target_id,
            words_count=words_count,
            due_count=due_count,
            created_at=_format_dt(created_at),
            last_activity=_format_dt(last_activity),
        ),
        reply_markup=admin_admin_add_confirm_kb(),
    )


@router.callback_query(F.data == "admin:admins")
async def admin_admins_menu(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_main_admin_callback(callback):
        return
    await state.set_state(AdminStates.admins_menu)
    await callback.message.edit_text(
        t("admin_admins.menu_title"), reply_markup=admin_admins_menu_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "admin:admins:add")
async def admin_admins_add_menu(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_main_admin_callback(callback):
        return
    await state.set_state(AdminStates.admins_add_method)
    await callback.message.edit_text(
        t("admin_admins.add_method_prompt"), reply_markup=admin_admins_add_method_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "admin:admins:add:id")
async def admin_admins_add_id_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_main_admin_callback(callback):
        return
    await state.set_state(AdminStates.admins_add_id)
    await callback.message.edit_text(
        t("admin_admins.add_id_prompt"),
        reply_markup=admin_admins_cancel_kb(),
    )
    await callback.answer()


@router.message(AdminStates.admins_add_id)
async def admin_admins_add_id_value(message: Message, state: FSMContext) -> None:
    if not await ensure_main_admin_message(message):
        return
    target_id = parse_int(message.text or "")
    if not target_id:
        await message.answer(
            t("admin_admins.invalid_id"),
            reply_markup=admin_admins_cancel_kb(),
        )
        return
    main_id = get_main_admin_id()
    if main_id and target_id == main_id:
        await message.answer(
            t("admin_admins.already_admin"),
            reply_markup=admin_admins_cancel_kb(),
        )
        return
    if target_id in settings.admin_user_ids:
        await message.answer(
            t("admin_admins.already_admin"),
            reply_markup=admin_admins_cancel_kb(),
        )
        return
    await _render_preview(
        message,
        state,
        target_id=target_id,
        first_name=str(target_id),
        username=None,
    )


@router.callback_query(F.data == "admin:admins:add:forward")
async def admin_admins_add_forward_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_main_admin_callback(callback):
        return
    await state.set_state(AdminStates.admins_add_forward)
    await callback.message.edit_text(
        t("admin_admins.add_forward_prompt"),
        reply_markup=admin_admins_cancel_kb(),
    )
    await callback.answer()


@router.message(AdminStates.admins_add_forward)
async def admin_admins_add_forward_message(message: Message, state: FSMContext) -> None:
    if not await ensure_main_admin_message(message):
        return
    forward_from = _extract_forward_user(message)
    if not forward_from:
        await message.answer(
            t("admin_admins.forward_missing"),
            reply_markup=admin_admins_cancel_kb(),
        )
        return
    target_id = forward_from.id
    main_id = get_main_admin_id()
    if main_id and target_id == main_id:
        await message.answer(
            t("admin_admins.already_admin"),
            reply_markup=admin_admins_cancel_kb(),
        )
        return
    if target_id in settings.admin_user_ids:
        await message.answer(
            t("admin_admins.already_admin"),
            reply_markup=admin_admins_cancel_kb(),
        )
        return
    await _render_preview(
        message,
        state,
        target_id=target_id,
        first_name=forward_from.first_name or str(target_id),
        username=forward_from.username,
    )


@router.callback_query(F.data == "admin:admins:add:confirm")
async def admin_admins_add_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_main_admin_callback(callback):
        return
    data = await state.get_data()
    target_id = data.get("pending_admin_id")
    name = data.get("pending_admin_name") or str(target_id)
    username = data.get("pending_admin_username")
    if not target_id:
        await callback.answer(t("admin_admins.user_not_found"), show_alert=True)
        return
    main_id = get_main_admin_id()
    if main_id and target_id == main_id:
        await callback.answer(t("admin_admins.already_admin"), show_alert=True)
        return
    async with AsyncSessionLocal() as session:
        if await get_admin(session, int(target_id)):
            await callback.answer(t("admin_admins.already_admin"), show_alert=True)
            return
        await upsert_admin(session, int(target_id), name, username, callback.from_user.id)
    settings.admin_user_ids.add(int(target_id))
    await state.clear()
    await callback.message.answer(t("admin_admins.added", name=name))
    await callback.answer()


@router.callback_query(F.data == "admin:admins:add:cancel")
async def admin_admins_add_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_main_admin_callback(callback):
        return
    await state.clear()
    await callback.message.edit_text(
        t("admin_admins.menu_title"), reply_markup=admin_admins_menu_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "admin:admins:list")
async def admin_admins_list(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_main_admin_callback(callback):
        return
    async with AsyncSessionLocal() as session:
        admins = await list_admins(session)
    items = []
    for admin in admins:
        marker = "👑" if admin.is_owner else "👤"
        items.append((admin.tg_user_id, f"{marker} {_display_name(admin)}"))
    await callback.message.edit_text(
        t("admin_admins.list_title"),
        reply_markup=admin_admins_list_kb(items),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:admins:view:"))
async def admin_admins_view(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_main_admin_callback(callback):
        return
    target_id = parse_int(callback.data.split(":")[-1])
    if not target_id:
        await callback.answer(t("admin_admins.user_not_found"), show_alert=True)
        return
    async with AsyncSessionLocal() as session:
        admin = await get_admin(session, target_id)
    if not admin:
        await callback.answer(t("admin_admins.user_not_found"), show_alert=True)
        return
    await callback.message.edit_text(
        t(
            "admin_admins.detail",
            name=_display_name(admin),
            username=admin.username or "—",
            tg_user_id=admin.tg_user_id,
            added_by=admin.added_by,
            added_at=_format_dt(admin.added_at),
            is_owner=t("admin_admins.owner_yes") if admin.is_owner else t("admin_admins.owner_no"),
        ),
        reply_markup=admin_admin_detail_kb(admin.is_owner, admin.tg_user_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:admins:remove:"))
async def admin_admins_remove_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_main_admin_callback(callback):
        return
    target_id = parse_int(callback.data.split(":")[-1])
    if not target_id:
        await callback.answer(t("admin_admins.user_not_found"), show_alert=True)
        return
    async with AsyncSessionLocal() as session:
        admin = await get_admin(session, target_id)
    if not admin:
        await callback.answer(t("admin_admins.user_not_found"), show_alert=True)
        return
    if admin.is_owner:
        await callback.answer(t("admin_admins.remove_blocked"), show_alert=True)
        return
    await callback.message.edit_text(
        t("admin_admins.remove_confirm", name=_display_name(admin)),
        reply_markup=admin_admin_remove_confirm_kb(target_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:admins:remove_confirm:"))
async def admin_admins_remove_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_main_admin_callback(callback):
        return
    target_id = parse_int(callback.data.split(":")[-1])
    if not target_id:
        await callback.answer(t("admin_admins.user_not_found"), show_alert=True)
        return
    async with AsyncSessionLocal() as session:
        admin = await get_admin(session, target_id)
        if not admin:
            await callback.answer(t("admin_admins.user_not_found"), show_alert=True)
            return
        if admin.is_owner:
            await callback.answer(t("admin_admins.remove_blocked"), show_alert=True)
            return
        removed = await remove_admin(session, target_id)
    if removed:
        settings.admin_user_ids.discard(target_id)
        await callback.message.answer(
            t("admin_admins.removed", name=_display_name(admin))
        )
    await callback.answer()


@router.message(Command("addadmin"))
async def admin_addadmin_command(message: Message, state: FSMContext) -> None:
    if not await ensure_main_admin_message(message):
        return
    parts = (message.text or "").split()
    if len(parts) != 2:
        await message.answer(t("admin_admins.command_usage"))
        return
    target_id = parse_int(parts[1])
    if not target_id:
        await message.answer(t("admin_admins.invalid_id"))
        return
    if target_id in settings.admin_user_ids:
        await message.answer(t("admin_admins.already_admin"))
        return
    await _render_preview(
        message,
        state,
        target_id=target_id,
        first_name=str(target_id),
        username=None,
    )
