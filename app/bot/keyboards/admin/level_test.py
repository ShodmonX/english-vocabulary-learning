from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b


def admin_level_test_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=b("admin_level_test.import_json"),
                    callback_data="admin:level_test:json",
                )
            ],
            [
                InlineKeyboardButton(
                    text=b("admin_level_test.add_manual"),
                    callback_data="admin:level_test:manual",
                )
            ],
            [InlineKeyboardButton(text=b("common.back"), callback_data="admin:menu")],
        ]
    )
