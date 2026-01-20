from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b


def admin_maintenance_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("admin_maint.reset_fsm"), callback_data="admin:maint:reset_fsm")],
            [InlineKeyboardButton(text=b("admin_maint.cleanup"), callback_data="admin:maint:cleanup")],
            [InlineKeyboardButton(text=b("admin_maint.logs"), callback_data="admin:maint:logs")],
            [InlineKeyboardButton(text=b("common.back"), callback_data="admin:menu")],
        ]
    )
