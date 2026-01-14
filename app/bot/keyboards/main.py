from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📚 Mashq qilish", callback_data="menu:training"),
                InlineKeyboardButton(text="➕ So‘z qo‘shish", callback_data="menu:add_word"),
            ],
            [
                InlineKeyboardButton(text="📊 Natijalar", callback_data="menu:stats"),
                InlineKeyboardButton(text="⚙️ Sozlamalar", callback_data="menu:settings"),
            ],
        ]
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
