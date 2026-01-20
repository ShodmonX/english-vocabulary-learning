from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b


def admin_srs_reset_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("admin_srs.reset_full"), callback_data="admin:srs:confirm:full")],
            [InlineKeyboardButton(text=b("admin_srs.reset_reps"), callback_data="admin:srs:confirm:reps")],
            [InlineKeyboardButton(text=b("common.confirm_no"), callback_data="admin:users")],
        ]
    )
