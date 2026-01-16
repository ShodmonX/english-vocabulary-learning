from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.handlers.admin.common import ensure_admin_callback
from app.bot.keyboards.admin.db_management import (
    admin_db_cleanup_confirm_kb,
    admin_db_confirm_kb,
    admin_db_list_kb,
    admin_db_menu_kb,
)
from app.config import settings
from app.db.repo.admin import log_admin_action
from app.db.session import AsyncSessionLocal
from app.services.db_backup.engine import (
    cleanup_auto_backups,
    create_backup,
    delete_backup,
    format_backup_line,
    is_backup_locked,
    list_backups,
    restore_from_backup,
)

router = Router()
PAGE_SIZE = 5


async def _slice_backups(page: int, kind: str) -> tuple[list[str], list[str], bool]:
    list_kind = None if kind == "all" else kind
    backups = await list_backups(list_kind)
    total = len(backups)
    start = page * PAGE_SIZE
    end = start + PAGE_SIZE
    items = backups[start:end]
    lines = [format_backup_line(item) for item in items]
    names = [item.filename for item in items]
    has_next = end < total
    return names, lines, has_next


@router.callback_query(F.data == "admin:db:menu")
async def admin_db_menu(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    await callback.message.edit_text("🗄 Database Management", reply_markup=admin_db_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "adb:backup")
async def admin_db_backup(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    if is_backup_locked():
        await callback.answer("⏳ Backup jarayoni davom etyapti.", show_alert=True)
        return
    await callback.message.edit_text("⏳ Backup yaratilmoqda...")
    try:
        info = await create_backup("manual")
    except Exception as exc:
        async with AsyncSessionLocal() as session:
            await log_admin_action(
                session, callback.from_user.id, "backup/manual/fail", "backup", _truncate(str(exc))
            )
        await callback.message.edit_text(f"⚠️ Backup xatosi: {exc}")
        await callback.answer()
        return
    async with AsyncSessionLocal() as session:
        await log_admin_action(session, callback.from_user.id, "backup/manual/success", "backup", info.filename)
    await callback.message.edit_text(
        "✅ Backup yaratildi\n"
        f"📄 {info.filename}\n"
        f"📦 Size: {info.size_bytes / 1024 / 1024:.2f} MB",
        reply_markup=admin_db_menu_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adb:l:"))
async def admin_db_list(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    parts = callback.data.split(":")
    kind = parts[-2]
    page = int(parts[-1])
    names, lines, has_next = await _slice_backups(page, kind)
    if not lines:
        await callback.message.edit_text("Hozircha backup yo‘q 🙂", reply_markup=admin_db_menu_kb())
        await callback.answer()
        return
    text = "📂 Backup list (newest):\n" + "\n".join(lines)
    await callback.message.edit_text(
        text,
        reply_markup=admin_db_list_kb("list", page, has_next, items=names, kind=kind),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adb:rl:"))
async def admin_db_restore_list(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    parts = callback.data.split(":")
    kind = parts[-2]
    page = int(parts[-1])
    names, lines, has_next = await _slice_backups(page, kind)
    if not lines:
        await callback.message.edit_text("Hozircha backup yo‘q 🙂", reply_markup=admin_db_menu_kb())
        await callback.answer()
        return
    text = "♻️ Restore uchun backup tanlang:\n" + "\n".join(lines)
    await callback.message.edit_text(
        text,
        reply_markup=admin_db_list_kb("restore", page, has_next, items=names, kind=kind),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adb:dl:"))
async def admin_db_delete_list(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    parts = callback.data.split(":")
    kind = parts[-2]
    page = int(parts[-1])
    names, lines, has_next = await _slice_backups(page, kind)
    if not lines:
        await callback.message.edit_text("Hozircha backup yo‘q 🙂", reply_markup=admin_db_menu_kb())
        await callback.answer()
        return
    text = "🧹 O‘chirish uchun backup tanlang:\n" + "\n".join(lines)
    await callback.message.edit_text(
        text,
        reply_markup=admin_db_list_kb("delete", page, has_next, items=names, kind=kind),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adb:i:"))
async def admin_db_info(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    parts = callback.data.split(":")
    kind = parts[-2]
    filename = parts[-1]
    backups = await list_backups()
    info = next((b for b in backups if b.filename == filename), None)
    if not info:
        await callback.answer("⚠️ Backup topilmadi.", show_alert=True)
        return
    await callback.message.edit_text(
        "ℹ️ Backup info:\n" + format_backup_line(info),
        reply_markup=admin_db_list_kb("list", 0, False, filename=filename, kind=kind),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adb:rp:"))
async def admin_db_restore_pick(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    filename = callback.data.split(":")[-1]
    await callback.message.edit_text(
        "⚠️ Bu amal hozirgi DB ni ALMASHTIRADI.\nDavom etasizmi?",
        reply_markup=admin_db_confirm_kb("restore", filename),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adb:dp:"))
async def admin_db_delete_pick(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    filename = callback.data.split(":")[-1]
    await callback.message.edit_text(
        "⚠️ Backupni o‘chirmoqchimisiz?",
        reply_markup=admin_db_confirm_kb("delete", filename),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adb:rc:"))
async def admin_db_restore_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    filename = callback.data.split(":")[-1]
    await callback.message.edit_text(
        "⚠️ Bu amal hozirgi DB ni ALMASHTIRADI.\nDavom etasizmi?",
        reply_markup=admin_db_confirm_kb("restore", filename),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adb:dc:"))
async def admin_db_delete_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    filename = callback.data.split(":")[-1]
    await callback.message.edit_text(
        "⚠️ Backupni o‘chirmoqchimisiz?",
        reply_markup=admin_db_confirm_kb("delete", filename),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adb:rr:"))
async def admin_db_restore_run(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    filename = callback.data.split(":")[-1]
    if is_backup_locked():
        await callback.answer("⏳ Backup/restore jarayoni davom etyapti.", show_alert=True)
        return
    await callback.message.edit_text("🛠 Maintenance mode yoqildi. Restore boshlanmoqda...")
    try:
        await restore_from_backup(filename)
    except Exception as exc:
        async with AsyncSessionLocal() as session:
            await log_admin_action(
                session, callback.from_user.id, "backup/restore/fail", "backup", _truncate(str(exc))
            )
        await callback.message.edit_text(f"⚠️ Restore xatosi: {exc}")
        await callback.answer()
        return
    async with AsyncSessionLocal() as session:
        await log_admin_action(session, callback.from_user.id, "backup/restore/success", "backup", filename)
    await callback.message.edit_text(
        "✅ DB muvaffaqiyatli tiklandi", reply_markup=admin_db_menu_kb()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adb:dr:"))
async def admin_db_delete_run(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    filename = callback.data.split(":")[-1]
    if is_backup_locked():
        await callback.answer("⏳ Backup/restore jarayoni davom etyapti.", show_alert=True)
        return
    try:
        await delete_backup(filename)
    except Exception as exc:
        async with AsyncSessionLocal() as session:
            await log_admin_action(
                session, callback.from_user.id, "backup/delete/fail", "backup", _truncate(str(exc))
            )
        await callback.message.edit_text(f"⚠️ O‘chirish xatosi: {exc}")
        await callback.answer()
        return
    async with AsyncSessionLocal() as session:
        await log_admin_action(session, callback.from_user.id, "backup/delete/success", "backup", filename)
    await callback.message.edit_text("✅ Backup o‘chirildi", reply_markup=admin_db_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "adb:auto:status")
async def admin_db_auto_status(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    text = (
        "🕒 Auto backup status:\n"
        f"Enabled: {settings.auto_backup_enabled}\n"
        f"Schedule: {settings.auto_backup_schedule} {settings.auto_backup_hour:02d}:{settings.auto_backup_minute:02d}\n"
        f"Retention (daily): {settings.auto_backup_retention_days} days\n"
        f"Prefix: {settings.auto_backup_prefix}\n"
        f"Dir: {settings.backup_dir}"
    )
    await callback.message.edit_text(text, reply_markup=admin_db_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "adb:cleanup:ask")
async def admin_db_cleanup_auto(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    await callback.message.edit_text(
        "⚠️ Auto backup’larni retention bo‘yicha tozalaysizmi?",
        reply_markup=admin_db_cleanup_confirm_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "adb:cleanup:run")
async def admin_db_cleanup_run(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    if is_backup_locked():
        await callback.answer("⏳ Backup/restore jarayoni davom etyapti.", show_alert=True)
        return
    try:
        deleted = await cleanup_auto_backups(settings.auto_backup_retention_days)
    except Exception as exc:
        async with AsyncSessionLocal() as session:
            await log_admin_action(
                session, callback.from_user.id, "backup/cleanup/fail", "backup", _truncate(str(exc))
            )
        await callback.message.edit_text(f"⚠️ Cleanup xatosi: {exc}")
        await callback.answer()
        return
    async with AsyncSessionLocal() as session:
        await log_admin_action(
            session, callback.from_user.id, "backup/cleanup/success", "backup", str(deleted)
        )
    await callback.message.edit_text(
        f"🧹 Cleanup tugadi. O‘chirildi: {deleted} ta.", reply_markup=admin_db_menu_kb()
    )
    await callback.answer()


def _truncate(text: str, max_len: int = 64) -> str:
    cleaned = text.strip()
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3] + "..."
