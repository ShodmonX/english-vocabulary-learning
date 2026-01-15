from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def leaderboard_settings_kb(opt_in: bool, show_username: bool) -> InlineKeyboardMarkup:
    opt_label = "✅ Ko‘rinish: ON" if opt_in else "🚫 Ko‘rinish: OFF"
    user_label = "👤 Username: ON" if show_username else "👤 Username: OFF"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=opt_label, callback_data="lb:settings:optin")],
            [InlineKeyboardButton(text="✍️ Public name", callback_data="lb:settings:alias")],
            [InlineKeyboardButton(text=user_label, callback_data="lb:settings:username")],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="lb:menu")],
        ]
    )
