from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def profile_refresh_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Yangilash", callback_data="profile:refresh")],
            [
                InlineKeyboardButton(
                    text="➕ Admin orqali to‘ldirish", callback_data="profile:topup:admin"
                ),
                InlineKeyboardButton(
                    text="⭐ Telegram Stars orqali", callback_data="profile:topup:stars"
                ),
            ],
        ]
    )


def profile_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Profilga qaytish", callback_data="profile:refresh")]]
    )


def stars_packages_kb(package_keys: list[str]) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text=f"⭐ {key}", callback_data=f"profile:stars:{key.lower()}")
        for key in package_keys
    ]
    rows = [buttons[i : i + 3] for i in range(0, len(buttons), 3)]
    rows.append([InlineKeyboardButton(text="⬅️ Profilga qaytish", callback_data="profile:refresh")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
