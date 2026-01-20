from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b


def language_kb(auto_translation_enabled: bool) -> InlineKeyboardMarkup:
    auto_label = (
        b("settings_language.auto_on")
        if auto_translation_enabled
        else b("settings_language.auto_off")
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("settings_language.base_lang"), callback_data="settings:language:base_lang")],
            [InlineKeyboardButton(text=auto_label, callback_data="settings:language:auto_toggle")],
            [InlineKeyboardButton(text=b("settings_language.engine"), callback_data="settings:language:engine")],
            [InlineKeyboardButton(text=b("settings_language.reset"), callback_data="settings:language:reset")],
            [InlineKeyboardButton(text=b("common.back"), callback_data="settings:menu")],
        ]
    )
