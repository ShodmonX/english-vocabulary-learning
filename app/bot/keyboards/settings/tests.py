from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b


def tests_kb(pronunciation_enabled: bool) -> InlineKeyboardMarkup:
    pron_label = (
        b("settings_tests.pron_on")
        if pronunciation_enabled
        else b("settings_tests.pron_off")
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=b("settings_tests.quiz_size"), callback_data="settings:tests:quiz_size"
                )
            ],
            [InlineKeyboardButton(text=pron_label, callback_data="settings:tests:pronunciation_toggle")],
            [
                InlineKeyboardButton(
                    text=b("settings_tests.pron_mode"), callback_data="settings:tests:pronunciation_mode"
                )
            ],
            [InlineKeyboardButton(text=b("settings_tests.reset"), callback_data="settings:tests:reset")],
            [InlineKeyboardButton(text=b("common.back"), callback_data="settings:menu")],
        ]
    )


def pronunciation_mode_kb(current: str) -> InlineKeyboardMarkup:
    def _label(value: str, text_key: str) -> str:
        text = b(text_key)
        return b("settings_tests.selected", text=text) if current == value else text

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=_label("single", "settings_tests.mode_single"),
                    callback_data="settings:tests:pronunciation_mode:single",
                )
            ],
            [
                InlineKeyboardButton(
                    text=_label("quiz", "settings_tests.mode_quiz"),
                    callback_data="settings:tests:pronunciation_mode:quiz",
                )
            ],
            [
                InlineKeyboardButton(
                    text=_label("both", "settings_tests.mode_both"),
                    callback_data="settings:tests:pronunciation_mode:both",
                )
            ],
            [InlineKeyboardButton(text=b("common.back"), callback_data="settings:tests")],
        ]
    )
