from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def main_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
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
        ],
        resize_keyboard=True,
    )


def training_kb(show_meaning: bool = False) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="📖 Ma'nosini ko‘rish", callback_data="train:show")]
    ]
    if show_meaning:
        buttons = []
    buttons.append(
        [
            InlineKeyboardButton(text="✅ Bilardim", callback_data="train:knew"),
            InlineKeyboardButton(text="🙂 Unutdim", callback_data="train:forgot"),
        ]
    )
    buttons.append(
        [
            InlineKeyboardButton(text="⏭️ O‘tkazib yuborish", callback_data="train:skip"),
            InlineKeyboardButton(text="🚪 Chiqish", callback_data="train:exit"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


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
