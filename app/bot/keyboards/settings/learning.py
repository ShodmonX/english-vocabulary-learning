from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def learning_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📚 Kuniga nechta so‘z?", callback_data="settings:learning:words_per_day"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔁 Takrorlash algoritmi", callback_data="settings:learning:srs"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔄 Defaultga qaytarish", callback_data="settings:learning:reset"
                )
            ],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="settings:menu")],
        ]
    )
