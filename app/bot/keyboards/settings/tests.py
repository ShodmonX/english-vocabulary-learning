from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def tests_kb(pronunciation_enabled: bool) -> InlineKeyboardMarkup:
    pron_label = "🗣 Talaffuz: ON" if pronunciation_enabled else "🗣 Talaffuz: OFF"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🧩 Quizdagi so‘zlar soni", callback_data="settings:tests:quiz_size"
                )
            ],
            [InlineKeyboardButton(text=pron_label, callback_data="settings:tests:pronunciation_toggle")],
            [
                InlineKeyboardButton(
                    text="🗣 Talaffuz rejimi", callback_data="settings:tests:pronunciation_mode"
                )
            ],
            [InlineKeyboardButton(text="🔄 Defaultga qaytarish", callback_data="settings:tests:reset")],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="settings:menu")],
        ]
    )


def pronunciation_mode_kb(current: str) -> InlineKeyboardMarkup:
    def _label(value: str, text: str) -> str:
        return f"✅ {text}" if current == value else text

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=_label("single", "Faqat bitta so‘z"),
                    callback_data="settings:tests:pronunciation_mode:single",
                )
            ],
            [
                InlineKeyboardButton(
                    text=_label("quiz", "Faqat quiz"),
                    callback_data="settings:tests:pronunciation_mode:quiz",
                )
            ],
            [
                InlineKeyboardButton(
                    text=_label("both", "Ikkalasi ham"),
                    callback_data="settings:tests:pronunciation_mode:both",
                )
            ],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="settings:tests")],
        ]
    )
