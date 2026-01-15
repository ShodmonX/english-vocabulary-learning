from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_content_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔍 User bo‘yicha so‘zlar", callback_data="admin:content:user")],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:menu")],
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
        nav.append(InlineKeyboardButton(text="◀️ Prev", callback_data=f"admin:content:page:{page-1}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="Next ▶️", callback_data=f"admin:content:page:{page+1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:content")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_content_detail_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ So‘zni tahrirlash", callback_data="admin:content:edit:word")],
            [InlineKeyboardButton(text="📝 Tarjimani tahrirlash", callback_data="admin:content:edit:translation")],
            [InlineKeyboardButton(text="💬 Misolni tahrirlash", callback_data="admin:content:edit:example")],
            [InlineKeyboardButton(text="🗑 O‘chirish", callback_data="admin:content:delete")],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:content:back")],
        ]
    )
