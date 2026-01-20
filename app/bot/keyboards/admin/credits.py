from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b


def admin_credits_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("admin_credits.add_id"), callback_data="admin:credits:add_id")],
            [
                InlineKeyboardButton(
                    text=b("admin_credits.forward"), callback_data="admin:credits:forward"
                )
            ],
            [InlineKeyboardButton(text=b("common.back"), callback_data="admin:menu")],
        ]
    )
