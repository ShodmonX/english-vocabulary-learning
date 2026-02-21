from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b


def admin_basic_limit_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("admin_settings.edit"), callback_data="admin:basic_limit:edit")],
            [InlineKeyboardButton(text=b("common.back"), callback_data="admin:menu")],
        ]
    )


def admin_full_test_charge_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=b("admin_settings.edit"),
                    callback_data="admin:full_test_charge:edit",
                )
            ],
            [InlineKeyboardButton(text=b("common.back"), callback_data="admin:menu")],
        ]
    )


def admin_test_limits_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=b("admin_settings.quick_count"),
                    callback_data="admin:test_limits:edit:quick_count",
                ),
                InlineKeyboardButton(
                    text=b("admin_settings.quick_time"),
                    callback_data="admin:test_limits:edit:quick_time",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=b("admin_settings.full_count"),
                    callback_data="admin:test_limits:edit:full_count",
                ),
                InlineKeyboardButton(
                    text=b("admin_settings.full_time"),
                    callback_data="admin:test_limits:edit:full_time",
                ),
            ],
            [InlineKeyboardButton(text=b("common.back"), callback_data="admin:menu")],
        ]
    )
