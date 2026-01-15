from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def leaderboard_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔥 Streak TOP", callback_data="lb:list:streak:0")],
            [InlineKeyboardButton(text="🏆 Longest Streak", callback_data="lb:list:longest:0")],
            [InlineKeyboardButton(text="📚 So‘zlar TOP", callback_data="lb:list:words:0")],
            [InlineKeyboardButton(text="⚙️ Reyting sozlamalari", callback_data="lb:settings")],
            [InlineKeyboardButton(text="◀️ Chiqish", callback_data="lb:exit")],
        ]
    )
