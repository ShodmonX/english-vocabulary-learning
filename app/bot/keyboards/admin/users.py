from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b


def admin_users_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("admin_users.search"), callback_data="admin:users:search")],
            [InlineKeyboardButton(text=b("common.back"), callback_data="admin:menu")],
        ]
    )


def admin_user_actions_kb(is_blocked: bool) -> InlineKeyboardMarkup:
    block_label = (
        b("admin_users.unblock") if is_blocked else b("admin_users.block")
    )
    block_action = "admin:users:unblock" if is_blocked else "admin:users:block"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=block_label, callback_data=block_action),
                InlineKeyboardButton(text=b("admin_users.srs_reset"), callback_data="admin:srs:reset"),
            ],
            [InlineKeyboardButton(text=b("admin_users.content"), callback_data="admin:content:open")],
            [InlineKeyboardButton(text=b("common.back"), callback_data="admin:users")],
        ]
    )


def admin_confirm_kb(confirm_cb: str, cancel_cb: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=b("common.confirm_yes"), callback_data=confirm_cb),
                InlineKeyboardButton(text=b("common.confirm_no"), callback_data=cancel_cb),
            ]
        ]
    )
