from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_db_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📦 Manual backup now", callback_data="adb:backup")],
            [InlineKeyboardButton(text="🕒 Auto backup status", callback_data="adb:auto:status")],
            [InlineKeyboardButton(text="🧹 Cleanup auto backups", callback_data="adb:cleanup:ask")],
            [InlineKeyboardButton(text="📂 Backup list (all)", callback_data="adb:l:all:0")],
            [InlineKeyboardButton(text="📂 Auto backups", callback_data="adb:l:auto:0")],
            [InlineKeyboardButton(text="📂 Manual backups", callback_data="adb:l:manual:0")],
            [InlineKeyboardButton(text="📂 Pre-restore backups", callback_data="adb:l:pre_restore:0")],
            [InlineKeyboardButton(text="♻️ Restore from backup", callback_data="adb:rl:all:0")],
            [InlineKeyboardButton(text="🧹 Delete backup", callback_data="adb:dl:all:0")],
            [InlineKeyboardButton(text="◀️ Back", callback_data="admin:menu")],
        ]
    )


def admin_db_list_kb(
    action: str,
    page: int,
    has_next: bool,
    items: list[str] | None = None,
    filename: str | None = None,
    kind: str = "all",
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if filename:
        if action == "restore":
            rows.append([InlineKeyboardButton(text="♻️ Restore", callback_data=f"adb:rc:{filename}")])
        elif action == "delete":
            rows.append([InlineKeyboardButton(text="🧹 Delete", callback_data=f"adb:dc:{filename}")])
        rows.append([InlineKeyboardButton(text="◀️ Back", callback_data=_list_cb(action, kind, page))])
        return InlineKeyboardMarkup(inline_keyboard=rows)

    if items:
        for name in items:
            row = [InlineKeyboardButton(text="ℹ️ Info", callback_data=f"adb:i:{kind}:{name}")]
            if action in {"restore", "list"}:
                row.append(
                    InlineKeyboardButton(
                        text="♻️ Restore", callback_data=f"adb:rp:{kind}:{name}"
                    )
                )
            if action in {"delete", "list"}:
                row.append(
                    InlineKeyboardButton(
                        text="🧹 Delete", callback_data=f"adb:dp:{kind}:{name}"
                    )
                )
            rows.append(row)

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Prev", callback_data=_list_cb(action, kind, page - 1)))
    if has_next:
        nav.append(InlineKeyboardButton(text="Next ▶️", callback_data=_list_cb(action, kind, page + 1)))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="◀️ Back", callback_data="admin:db:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_db_cleanup_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❌ Yo‘q", callback_data="admin:db:menu"),
                InlineKeyboardButton(text="✅ Ha, tozalash", callback_data="adb:cleanup:run"),
            ]
        ]
    )


def _list_cb(action: str, kind: str, page: int) -> str:
    mapping = {
        "list": "adb:l",
        "restore": "adb:rl",
        "delete": "adb:dl",
    }
    prefix = mapping.get(action, "adb:l")
    return f"{prefix}:{kind}:{page}"


def admin_db_confirm_kb(action: str, filename: str) -> InlineKeyboardMarkup:
    ok = "⚠️ HA, TIKLASH" if action == "restore" else "✅ Ha, o‘chirish"
    action_map = {"restore": "adb:rr", "delete": "adb:dr"}
    prefix = action_map.get(action, "adb:rr")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="❌ Yo‘q", callback_data="admin:db:menu"),
                InlineKeyboardButton(text=ok, callback_data=f"{prefix}:{filename}"),
            ]
        ]
    )
