from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b


def admin_content_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("admin_content.by_user"), callback_data="admin:content:user")],
            [InlineKeyboardButton(text=b("common.back"), callback_data="admin:menu")],
        ]
    )


def admin_content_list_kb(
    items: list[tuple[int, str]],
    page: int,
    has_next: bool,
    context: str = "content",
) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"admin:content:open:{word_id}")]
        for word_id, label in items
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text=b("common.prev"), callback_data=f"admin:content:page:{page-1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text=b("common.next"), callback_data=f"admin:content:page:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text=b("common.back"), callback_data="admin:content")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_content_detail_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("admin_content.edit_word"), callback_data="admin:content:edit:word")],
            [InlineKeyboardButton(text=b("admin_content.edit_translation"), callback_data="admin:content:edit:translation")],
            [InlineKeyboardButton(text=b("admin_content.edit_example"), callback_data="admin:content:edit:example")],
            [InlineKeyboardButton(text=b("admin_content.delete"), callback_data="admin:content:delete")],
            [InlineKeyboardButton(text=b("common.back"), callback_data="admin:content:back")],
        ]
    )
