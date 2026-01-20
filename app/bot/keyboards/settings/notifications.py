from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b


def notifications_kb(enabled: bool) -> InlineKeyboardMarkup:
    label = (
        b("settings_notifications.status_on")
        if enabled
        else b("settings_notifications.status_off")
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data="settings:notifications:toggle")],
            [InlineKeyboardButton(text=b("settings_notifications.time"), callback_data="settings:notifications:time")],
            [InlineKeyboardButton(text=b("settings_notifications.reset"), callback_data="settings:notifications:reset")],
            [InlineKeyboardButton(text=b("common.back"), callback_data="settings:menu")],
        ]
    )
