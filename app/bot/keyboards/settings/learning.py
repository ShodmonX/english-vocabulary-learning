from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b


def learning_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=b("settings_learning.words_per_day"), callback_data="settings:learning:words_per_day"
                )
            ],
            [
                InlineKeyboardButton(
                    text=b("settings_learning.srs"), callback_data="settings:learning:srs"
                )
            ],
            [
                InlineKeyboardButton(
                    text=b("settings_learning.reset"), callback_data="settings:learning:reset"
                )
            ],
            [InlineKeyboardButton(text=b("common.back"), callback_data="settings:menu")],
        ]
    )
