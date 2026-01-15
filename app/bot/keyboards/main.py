from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def main_menu_kb(is_admin: bool = False, streak: int | None = None) -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(text="📚 Mashq qilish"),
            KeyboardButton(text="🧩 Quiz"),
        ],
        [
            KeyboardButton(text="➕ So‘z qo‘shish"),
            KeyboardButton(text="📊 Natijalar"),
        ],
        [
            KeyboardButton(text="🗂 So‘zlarim"),
            KeyboardButton(text="⚙️ Sozlamalar"),
        ],
        [KeyboardButton(text="🗣 Talaffuz")],
    ]
    if is_admin:
        keyboard.append([KeyboardButton(text="🛠 Admin")])
    if streak and streak > 0:
        keyboard.append([KeyboardButton(text=f"🔥 {streak} kun")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def settings_kb(reminder_enabled: bool = True) -> InlineKeyboardMarkup:
    reminder_label = "🔔 Eslatma: ON" if reminder_enabled else "🔕 Eslatma: OFF"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎯 Kunlik maqsad", callback_data="settings:daily_goal")],
            [InlineKeyboardButton(text="⏰ Eslatma vaqti", callback_data="settings:reminder_time")],
            [InlineKeyboardButton(text=reminder_label, callback_data="settings:reminder_toggle")],
            [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="settings:back")],
        ]
    )
