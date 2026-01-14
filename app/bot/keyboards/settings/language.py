from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def language_kb(auto_translation_enabled: bool) -> InlineKeyboardMarkup:
    auto_label = (
        "🤖 Avto tarjima: ON" if auto_translation_enabled else "🤖 Avto tarjima: OFF"
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🌍 Asosiy til", callback_data="settings:language:base_lang")],
            [InlineKeyboardButton(text=auto_label, callback_data="settings:language:auto_toggle")],
            [InlineKeyboardButton(text="🔄 Tarjima engine", callback_data="settings:language:engine")],
            [InlineKeyboardButton(text="🔄 Defaultga qaytarish", callback_data="settings:language:reset")],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="settings:menu")],
        ]
    )
