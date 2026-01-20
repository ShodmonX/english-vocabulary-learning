from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_packages_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✏️ BASIC", callback_data="admin:packages:edit:BASIC"),
                InlineKeyboardButton(text="✏️ STANDARD", callback_data="admin:packages:edit:STANDARD"),
                InlineKeyboardButton(text="✏️ PRO", callback_data="admin:packages:edit:PRO"),
            ],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:menu")],
        ]
    )


def admin_package_edit_kb(package_key: str, is_active: bool) -> InlineKeyboardMarkup:
    toggle_label = "⛔️ O‘chirish" if is_active else "✅ Aktiv qilish"
    toggle_value = "off" if is_active else "on"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="💰 Manual narx (UZS) o‘zgartirish",
                    callback_data=f"admin:packages:manual:{package_key}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐ Stars narx o‘zgartirish",
                    callback_data=f"admin:packages:stars:{package_key}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=toggle_label,
                    callback_data=f"admin:packages:toggle:{package_key}:{toggle_value}",
                )
            ],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin:packages")],
        ]
    )
