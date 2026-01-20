from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b


def limits_kb(enabled: bool) -> InlineKeyboardMarkup:
    label = (
        b("settings_limits.status_on")
        if enabled
        else b("settings_limits.status_off")
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data="settings:limits:toggle")],
            [
                InlineKeyboardButton(
                    text=b("settings_limits.pronunciation"),
                    callback_data="settings:limits:pronunciation",
                )
            ],
            [
                InlineKeyboardButton(
                    text=b("settings_limits.quiz"), callback_data="settings:limits:quiz"
                )
            ],
            [InlineKeyboardButton(text=b("settings_limits.reset"), callback_data="settings:limits:reset")],
            [InlineKeyboardButton(text=b("common.back"), callback_data="settings:menu")],
        ]
    )
