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


def admin_level_test_manual_level_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="A1", callback_data="admin:level_test:manual:level:A1"),
                InlineKeyboardButton(text="A2", callback_data="admin:level_test:manual:level:A2"),
                InlineKeyboardButton(text="B1", callback_data="admin:level_test:manual:level:B1"),
            ],
            [
                InlineKeyboardButton(text="B2", callback_data="admin:level_test:manual:level:B2"),
                InlineKeyboardButton(text="C1", callback_data="admin:level_test:manual:level:C1"),
                InlineKeyboardButton(text="C2", callback_data="admin:level_test:manual:level:C2"),
            ],
            [InlineKeyboardButton(text=b("common.back"), callback_data="admin:level_test")],
        ]
    )


def admin_level_test_manual_difficulty_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="1", callback_data="admin:level_test:manual:difficulty:1"),
                InlineKeyboardButton(text="2", callback_data="admin:level_test:manual:difficulty:2"),
                InlineKeyboardButton(text="3", callback_data="admin:level_test:manual:difficulty:3"),
                InlineKeyboardButton(text="4", callback_data="admin:level_test:manual:difficulty:4"),
                InlineKeyboardButton(text="5", callback_data="admin:level_test:manual:difficulty:5"),
            ],
            [InlineKeyboardButton(text=b("common.back"), callback_data="admin:level_test")],
        ]
    )


def admin_level_test_manual_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="MCQ", callback_data="admin:level_test:manual:type:MCQ"),
                InlineKeyboardButton(text="TYPING", callback_data="admin:level_test:manual:type:TYPING"),
            ],
            [InlineKeyboardButton(text=b("common.back"), callback_data="admin:level_test")],
        ]
    )


def admin_level_test_manual_skip_kb(skip_callback_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("admin_level_test.skip"), callback_data=skip_callback_data)],
            [InlineKeyboardButton(text=b("common.back"), callback_data="admin:level_test")],
        ]
    )


def admin_level_test_manual_active_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=b("admin_level_test.active_yes"),
                    callback_data="admin:level_test:manual:active:yes",
                ),
                InlineKeyboardButton(
                    text=b("admin_level_test.active_no"),
                    callback_data="admin:level_test:manual:active:no",
                ),
            ],
            [InlineKeyboardButton(text=b("common.back"), callback_data="admin:level_test")],
        ]
    )
