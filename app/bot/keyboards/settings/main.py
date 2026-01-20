from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b


def settings_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("settings_menu.learning"), callback_data="settings:learning")],
            [InlineKeyboardButton(text=b("settings_menu.tests"), callback_data="settings:tests")],
            [InlineKeyboardButton(text=b("settings_menu.language"), callback_data="settings:language")],
            [InlineKeyboardButton(text=b("settings_menu.notifications"), callback_data="settings:notifications")],
            [InlineKeyboardButton(text=b("settings_menu.limits"), callback_data="settings:limits")],
            [InlineKeyboardButton(text=b("settings_menu.advanced"), callback_data="settings:advanced")],
            [InlineKeyboardButton(text=b("common.back"), callback_data="settings:back")],
        ]
    )
