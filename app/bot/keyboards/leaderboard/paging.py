from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def leaderboard_paging_kb(
    list_type: str, page: int, has_next: bool
) -> InlineKeyboardMarkup:
    nav = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                text="◀️ Prev", callback_data=f"lb:list:{list_type}:{page-1}"
            )
        )
    if has_next:
        nav.append(
            InlineKeyboardButton(
                text="Next ▶️", callback_data=f"lb:list:{list_type}:{page+1}"
            )
        )
    rows = []
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="lb:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
