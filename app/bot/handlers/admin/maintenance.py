from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.handlers.admin.common import ensure_admin_callback
from app.bot.keyboards.admin.maintenance import admin_maintenance_kb
from app.db.repo.admin import log_admin_action
from app.db.session import AsyncSessionLocal
from app.services.log_buffer import get_last_errors

router = Router()


@router.callback_query(F.data == "admin:maintenance")
async def admin_maintenance_menu(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    await callback.message.edit_text("🧪 Debug / Maintenance:", reply_markup=admin_maintenance_kb())
    await callback.answer()


@router.callback_query(F.data == "admin:maint:reset_fsm")
async def admin_reset_fsm(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    await state.clear()
    async with AsyncSessionLocal() as session:
        await log_admin_action(session, callback.from_user.id, "fsm_reset", "system", None)
    await callback.message.answer("✅ FSM reset qilindi.")
    await callback.answer()


@router.callback_query(F.data == "admin:maint:cleanup")
async def admin_cleanup_temp(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    removed = _cleanup_temp_files()
    async with AsyncSessionLocal() as session:
        await log_admin_action(session, callback.from_user.id, "cleanup_temp", "system", None)
    await callback.message.answer(f"🧹 Temp fayllar tozalandi: {removed} ta.")
    await callback.answer()


@router.callback_query(F.data == "admin:maint:logs")
async def admin_show_logs(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    errors = get_last_errors(10)
    text = "📄 So‘nggi error log’lar:\n"
    text += "\n".join(errors) if errors else "—"
    await callback.message.answer(text)
    await callback.answer()


def _cleanup_temp_files() -> int:
    tmp_dir = Path(tempfile.gettempdir())
    cutoff = datetime.utcnow() - timedelta(hours=12)
    removed = 0
    for path in tmp_dir.iterdir():
        if not path.is_file():
            continue
        if path.suffix not in {".ogg", ".wav"}:
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        if datetime.utcfromtimestamp(stat.st_mtime) > cutoff:
            continue
        try:
            os.remove(path)
            removed += 1
        except OSError:
            continue
    return removed
