from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def limits_kb(enabled: bool) -> InlineKeyboardMarkup:
    label = "🔒 Limitlar: ON" if enabled else "🔓 Limitlar: OFF"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=label, callback_data="settings:limits:toggle")],
            [
                InlineKeyboardButton(
                    text="⚡ Kunlik talaffuz limiti",
                    callback_data="settings:limits:pronunciation",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚡ Quiz limiti (tez kunda)", callback_data="settings:limits:quiz"
                )
            ],
            [InlineKeyboardButton(text="🔄 Defaultga qaytarish", callback_data="settings:limits:reset")],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="settings:menu")],
        ]
    )
