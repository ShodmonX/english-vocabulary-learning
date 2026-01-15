from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_srs_reset_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ To‘liq reset", callback_data="admin:srs:confirm:full")],
            [InlineKeyboardButton(text="♻️ Faqat repetitions=0", callback_data="admin:srs:confirm:reps")],
            [InlineKeyboardButton(text="❌ Bekor", callback_data="admin:users")],
        ]
    )
