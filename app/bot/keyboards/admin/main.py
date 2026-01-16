from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Umumiy statistika", callback_data="admin:stats")],
            [InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="admin:users")],
            [InlineKeyboardButton(text="🧠 SRS nazorati", callback_data="admin:srs")],
            [InlineKeyboardButton(text="📘 Kontent nazorati", callback_data="admin:content")],
            [InlineKeyboardButton(text="🗄 Database Management", callback_data="admin:db:menu")],
            [InlineKeyboardButton(text="⚙️ Feature flag’lar", callback_data="admin:features")],
            [InlineKeyboardButton(text="🧪 Debug / Maintenance", callback_data="admin:maintenance")],
            [InlineKeyboardButton(text="🚪 Chiqish", callback_data="admin:exit")],
        ]
    )


def admin_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:menu")]]
    )
