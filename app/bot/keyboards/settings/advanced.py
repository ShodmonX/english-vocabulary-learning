from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b


def advanced_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=b("settings_advanced.reset_all"),
                    callback_data="settings:advanced:reset",
                )
            ],
            [
                InlineKeyboardButton(
                    text=b("settings_advanced.clear_sessions"),
                    callback_data="settings:advanced:clear_sessions",
                )
            ],
            [InlineKeyboardButton(text=b("common.confirm_no"), callback_data="settings:menu")],
        ]
    )


def advanced_reset_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("settings_advanced.reset_confirm"), callback_data="settings:advanced:reset_confirm")],
            [InlineKeyboardButton(text=b("common.confirm_no"), callback_data="settings:menu")],
        ]
    )
