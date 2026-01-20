from __future__ import annotations

import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.admin.common import ensure_admin_callback, ensure_admin_message
from app.bot.handlers.admin.states import AdminStates
from app.bot.keyboards.admin.main import admin_back_kb
from app.db.repo.admin import log_admin_action
from app.db.repo.app_settings import get_admin_contact_username, set_admin_contact_username
from app.db.session import AsyncSessionLocal
from app.services.i18n import t

router = Router()

_USERNAME_RE = re.compile(r"^@[A-Za-z0-9_]{3,32}$")


def _normalize_username(value: str) -> str | None:
    cleaned = value.strip()
    if cleaned == "-":
        return None
    if not cleaned:
        return ""
    if not cleaned.startswith("@"):
        cleaned = f"@{cleaned}"
    return cleaned


@router.callback_query(F.data == "admin:contact")
async def admin_contact_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    async with AsyncSessionLocal() as session:
        current = await get_admin_contact_username(session)
    current_text = current or t("admin_contact.not_set")
    await state.set_state(AdminStates.admin_contact_username)
    await callback.message.edit_text(
        t("admin_contact.prompt", username=current_text),
        reply_markup=admin_back_kb(),
    )
    await callback.answer()


@router.message(AdminStates.admin_contact_username)
async def admin_contact_save(message: Message, state: FSMContext) -> None:
    if not await ensure_admin_message(message):
        return
    normalized = _normalize_username(message.text or "")
    if normalized == "":
        await message.answer(t("admin_contact.invalid"))
        return
    if normalized is not None and not _USERNAME_RE.match(normalized):
        await message.answer(t("admin_contact.invalid"))
        return
    async with AsyncSessionLocal() as session:
        await set_admin_contact_username(session, normalized)
        await log_admin_action(
            session,
            message.from_user.id,
            "admin_contact_username_update",
            "app_setting",
            "admin_contact_username",
        )
    await state.set_state(AdminStates.menu)
    if normalized is None:
        await message.answer(t("admin_contact.cleared"), reply_markup=admin_back_kb())
    else:
        await message.answer(t("admin_contact.saved", username=normalized), reply_markup=admin_back_kb())
