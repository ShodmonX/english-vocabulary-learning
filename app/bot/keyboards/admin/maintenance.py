from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_maintenance_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="♻️ FSM reset (men)", callback_data="admin:maint:reset_fsm")],
            [InlineKeyboardButton(text="🧹 Temp fayllarni tozalash", callback_data="admin:maint:cleanup")],
            [InlineKeyboardButton(text="📄 So‘nggi error loglar", callback_data="admin:maint:logs")],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:menu")],
        ]
    )
