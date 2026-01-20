from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b


def admin_basic_limit_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("admin_settings.edit"), callback_data="admin:basic_limit:edit")],
            [InlineKeyboardButton(text=b("common.back"), callback_data="admin:menu")],
        ]
    )
