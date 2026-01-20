from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def profile_refresh_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔄 Yangilash", callback_data="profile:refresh")]]
    )
