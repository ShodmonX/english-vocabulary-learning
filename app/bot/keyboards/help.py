from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b


def help_menu_kb(is_admin: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=b("help.quick"), callback_data="help:quick:0")],
        [InlineKeyboardButton(text=b("help.add"), callback_data="help:add:0")],
        [InlineKeyboardButton(text=b("help.srs"), callback_data="help:srs:0")],
        [InlineKeyboardButton(text=b("help.quiz"), callback_data="help:quiz:0")],
        [InlineKeyboardButton(text=b("help.pron"), callback_data="help:pron:0")],
        [InlineKeyboardButton(text=b("help.words"), callback_data="help:words:0")],
        [InlineKeyboardButton(text=b("help.settings"), callback_data="help:settings:0")],
        [InlineKeyboardButton(text=b("help.trouble"), callback_data="help:trouble:0")],
        [InlineKeyboardButton(text=b("help.privacy"), callback_data="help:privacy:0")],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton(text=b("help.admin"), callback_data="help:admin:0")])
    rows.append([InlineKeyboardButton(text=b("help.exit"), callback_data="help:exit")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def help_page_kb(section: str, page: int, pages: int) -> InlineKeyboardMarkup:
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text=b("common.prev_page"), callback_data=f"help:{section}:{page-1}"))
    if page + 1 < pages:
        nav.append(InlineKeyboardButton(text=b("common.next_page"), callback_data=f"help:{section}:{page+1}"))
    rows = []
    if nav:
        rows.append(nav)
    rows.append(
        [
            InlineKeyboardButton(text=b("common.back"), callback_data="help:menu"),
            InlineKeyboardButton(text=b("help.menu"), callback_data="help:exit"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
