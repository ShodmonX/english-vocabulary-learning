from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def help_menu_kb(is_admin: bool) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="📌 Tez start", callback_data="help:quick:0")],
        [InlineKeyboardButton(text="➕ So‘z qo‘shish", callback_data="help:add:0")],
        [InlineKeyboardButton(text="🔁 Bugungi takrorlash", callback_data="help:srs:0")],
        [InlineKeyboardButton(text="🧩 Quiz", callback_data="help:quiz:0")],
        [InlineKeyboardButton(text="🗣 Talaffuz", callback_data="help:pron:0")],
        [InlineKeyboardButton(text="🗂 So‘zlarim", callback_data="help:words:0")],
        [InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="help:settings:0")],
        [InlineKeyboardButton(text="🧩 Muammolar", callback_data="help:trouble:0")],
        [InlineKeyboardButton(text="🔐 Maxfiylik", callback_data="help:privacy:0")],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton(text="🛠 Admin", callback_data="help:admin:0")])
    rows.append([InlineKeyboardButton(text="◀️ Chiqish", callback_data="help:exit")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def help_page_kb(section: str, page: int, pages: int) -> InlineKeyboardMarkup:
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Oldingi", callback_data=f"help:{section}:{page-1}"))
    if page + 1 < pages:
        nav.append(InlineKeyboardButton(text="Keyingi ▶️", callback_data=f"help:{section}:{page+1}"))
    rows = []
    if nav:
        rows.append(nav)
    rows.append(
        [
            InlineKeyboardButton(text="◀️ Orqaga", callback_data="help:menu"),
            InlineKeyboardButton(text="🏁 Menyuga", callback_data="help:exit"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
