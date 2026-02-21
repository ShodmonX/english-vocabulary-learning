from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b


def reminder_practice_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=b("practice.quick"),
                    callback_data="practice:mode:quick",
                )
            ]
        ]
    )
