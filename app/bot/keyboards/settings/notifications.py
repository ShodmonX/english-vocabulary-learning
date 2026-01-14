from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def notifications_kb(enabled: bool) -> InlineKeyboardMarkup:
    label = "🔔 Eslatmalar: ON" if enabled else "🔕 Eslatmalar: OFF"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data="settings:notifications:toggle")],
            [InlineKeyboardButton(text="⏰ Eslatma vaqti", callback_data="settings:notifications:time")],
            [InlineKeyboardButton(text="🔄 Defaultga qaytarish", callback_data="settings:notifications:reset")],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="settings:menu")],
        ]
    )
