from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b


def leaderboard_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("leaderboard.streak_top"), callback_data="lb:list:streak:0")],
            [InlineKeyboardButton(text=b("leaderboard.longest"), callback_data="lb:list:longest:0")],
            [InlineKeyboardButton(text=b("leaderboard.words_top"), callback_data="lb:list:words:0")],
            [InlineKeyboardButton(text=b("leaderboard.settings"), callback_data="lb:settings")],
            [InlineKeyboardButton(text=b("leaderboard.exit"), callback_data="lb:exit")],
        ]
    )
