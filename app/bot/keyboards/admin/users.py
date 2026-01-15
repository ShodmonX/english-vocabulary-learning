from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_users_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔍 User qidirish", callback_data="admin:users:search")],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:menu")],
        ]
    )


def admin_user_actions_kb(is_blocked: bool) -> InlineKeyboardMarkup:
    block_label = "🔓 Blokdan chiqarish" if is_blocked else "🚫 Userni bloklash"
    block_action = "admin:users:unblock" if is_blocked else "admin:users:block"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=block_label, callback_data=block_action)],
            [InlineKeyboardButton(text="🧠 SRS reset", callback_data="admin:srs:reset")],
            [InlineKeyboardButton(text="📘 Kontent", callback_data="admin:content:user")],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:users")],
        ]
    )


def admin_confirm_kb(confirm_cb: str, cancel_cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha", callback_data=confirm_cb),
                InlineKeyboardButton(text="❌ Bekor", callback_data=cancel_cb),
            ]
        ]
    )
