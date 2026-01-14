from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def settings_main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧠 O‘rganish", callback_data="settings:learning")],
            [InlineKeyboardButton(text="🧩 Testlar", callback_data="settings:tests")],
            [InlineKeyboardButton(text="🌍 Til & Tarjima", callback_data="settings:language")],
            [InlineKeyboardButton(text="🔔 Bildirishnomalar", callback_data="settings:notifications")],
            [InlineKeyboardButton(text="⚡ Cheklovlar", callback_data="settings:limits")],
            [InlineKeyboardButton(text="🛠 Texnik", callback_data="settings:advanced")],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="settings:back")],
        ]
    )
