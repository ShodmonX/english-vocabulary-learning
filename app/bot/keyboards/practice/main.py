from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def practice_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚡ Tezkor mashq", callback_data="practice:mode:quick")],
            [InlineKeyboardButton(text="🧠 O‘ylab javob berish", callback_data="practice:mode:recall")],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="practice:exit")],
        ]
    )


def practice_quick_step_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👀 Ma’nosini ko‘rish", callback_data="practice:quick:show"),
                InlineKeyboardButton(text="⏭ O‘tkazib yuborish", callback_data="practice:quick:skip"),
            ],
            [InlineKeyboardButton(text="🛑 To‘xtatish", callback_data="practice:stop")],
        ]
    )


def practice_quick_rate_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="😕 Bilmayman", callback_data="practice:rate:again"),
                InlineKeyboardButton(text="😐 Qiyin", callback_data="practice:rate:hard"),
            ],
            [
                InlineKeyboardButton(text="🙂 Yaxshi", callback_data="practice:rate:good"),
                InlineKeyboardButton(text="😄 Oson", callback_data="practice:rate:easy"),
            ],
            [InlineKeyboardButton(text="🛑 To‘xtatish", callback_data="practice:stop")],
        ]
    )


def practice_recall_prompt_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭ O‘tkazib yuborish", callback_data="practice:recall:skip")],
            [InlineKeyboardButton(text="🛑 To‘xtatish", callback_data="practice:stop")],
        ]
    )


def practice_summary_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔁 Yana mashq", callback_data="practice:again")],
            [InlineKeyboardButton(text="🧠 Rejimni almashtirish", callback_data="practice:menu")],
            [InlineKeyboardButton(text="🏁 Menyuga", callback_data="practice:exit")],
        ]
    )


def practice_due_empty_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Yangi so‘zlar bilan mashq", callback_data="practice:due:new")],
            [InlineKeyboardButton(text="◀️ Menyuga qaytish", callback_data="practice:due:exit")],
        ]
    )
