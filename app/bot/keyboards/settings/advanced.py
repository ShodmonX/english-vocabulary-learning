from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def advanced_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 Barcha sozlamalarni reset qilish",
                    callback_data="settings:advanced:reset",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🧹 Sessionlarni tozalash",
                    callback_data="settings:advanced:clear_sessions",
                )
            ],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="settings:menu")],
        ]
    )


def advanced_reset_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Ha, reset", callback_data="settings:advanced:reset_confirm")],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="settings:menu")],
        ]
    )
