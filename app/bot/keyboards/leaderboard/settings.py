from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b


def leaderboard_settings_kb(opt_in: bool, show_username: bool) -> InlineKeyboardMarkup:
    opt_label = b("leaderboard.opt_on") if opt_in else b("leaderboard.opt_off")
    user_label = b("leaderboard.username_on") if show_username else b("leaderboard.username_off")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=opt_label, callback_data="lb:settings:optin")],
            [InlineKeyboardButton(text=b("leaderboard.alias"), callback_data="lb:settings:alias")],
            [InlineKeyboardButton(text=user_label, callback_data="lb:settings:username")],
            [InlineKeyboardButton(text=b("common.back"), callback_data="lb:menu")],
        ]
    )
