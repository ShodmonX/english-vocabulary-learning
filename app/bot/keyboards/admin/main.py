from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b


def admin_menu_kb(is_owner: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=b("admin.stats"), callback_data="admin:stats"),
        InlineKeyboardButton(text=b("admin.users"), callback_data="admin:users"),
        InlineKeyboardButton(text=b("admin.srs"), callback_data="admin:srs"),
        InlineKeyboardButton(text=b("admin.content"), callback_data="admin:content"),
        InlineKeyboardButton(text=b("admin.packages"), callback_data="admin:packages"),
        InlineKeyboardButton(text=b("admin.credits"), callback_data="admin:credits"),
        InlineKeyboardButton(text=b("admin.contact"), callback_data="admin:contact"),
        InlineKeyboardButton(text=b("admin.db_management"), callback_data="admin:db:menu"),
        InlineKeyboardButton(text=b("admin.features"), callback_data="admin:features"),
        InlineKeyboardButton(text=b("admin.maintenance"), callback_data="admin:maintenance"),
    ]
    if is_owner:
        buttons.append(InlineKeyboardButton(text=b("admin.admins"), callback_data="admin:admins"))
        buttons.append(
            InlineKeyboardButton(text=b("admin.global_limit"), callback_data="admin:basic_limit")
        )
    buttons.append(InlineKeyboardButton(text=b("admin.exit"), callback_data="admin:exit"))
    rows = [buttons[i : i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=b("common.back"), callback_data="admin:menu")]]
    )
