from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_credits_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ ID orqali kredit", callback_data="admin:credits:add_id")],
            [
                InlineKeyboardButton(
                    text="📨 Forward orqali kredit", callback_data="admin:credits:forward"
                )
            ],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:menu")],
        ]
    )
