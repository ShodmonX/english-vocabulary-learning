from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def pronunciation_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎯 Bitta so‘z tekshirish", callback_data="pron:menu:single")],
            [InlineKeyboardButton(text="🧩 Talaffuz quiz", callback_data="pron:menu:quiz")],
            [InlineKeyboardButton(text="🎯 Tanlab talaffuz quiz", callback_data="pron:menu:select")],
        ]
    )


def single_mode_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🕒 Oxirgilar", callback_data="pron:single:recent")],
            [InlineKeyboardButton(text="🔎 Qidirish", callback_data="pron:single:search")],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="pron:menu:back")],
        ]
    )


def results_kb(items: list[tuple[int, str]], page: int, context: str, has_next: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for word_id, label in items:
        rows.append([InlineKeyboardButton(text=label, callback_data=f"pron:pick:{word_id}:{context}:{page}")])

    nav_row: list[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"pron:{context}:page:{page-1}")
        )
    nav_row.append(InlineKeyboardButton(text="🏠 Menyu", callback_data="pron:menu"))
    if has_next:
        nav_row.append(
            InlineKeyboardButton(text="➡️ Keyingi", callback_data=f"pron:{context}:page:{page+1}")
        )
    rows.append(nav_row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def single_word_kb(context: str, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔁 Boshqa so‘z", callback_data=f"pron:single:choose:{context}:{page}")],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data=f"pron:back:{context}:{page}")],
            [InlineKeyboardButton(text="🏁 Menyuga qaytish", callback_data="pron:exit")],
        ]
    )


def single_result_kb(context: str, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔁 Qayta urinib ko‘rish", callback_data=f"pron:retry:{context}:{page}")],
            [InlineKeyboardButton(text="🗂 Boshqa so‘z", callback_data=f"pron:single:choose:{context}:{page}")],
            [InlineKeyboardButton(text="🏁 Menyuga qaytish", callback_data="pron:exit")],
        ]
    )


def quiz_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🛑 Quizni to‘xtatish", callback_data="pron:quiz:stop")]]
    )


def quiz_done_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔁 Yana quiz", callback_data="pron:menu:quiz")],
            [InlineKeyboardButton(text="🏁 Menyuga qaytish", callback_data="pron:exit")],
        ]
    )


def select_menu_kb(selected_count: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🕒 Oxirgilar", callback_data="pron:select:recent")],
            [InlineKeyboardButton(text="🔎 Qidirish", callback_data="pron:select:search")],
            [
                InlineKeyboardButton(
                    text=f"✅ Tanlanganlar ({selected_count})", callback_data="pron:select:view"
                )
            ],
            [InlineKeyboardButton(text="▶️ Quizni boshlash", callback_data="pron:select:start")],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="pron:menu:back")],
        ]
    )


def select_results_kb(
    items: list[tuple[int, str]],
    selected_ids: set[int],
    page: int,
    context: str,
    has_next: bool,
    selected_count: int,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for word_id, label in items:
        prefix = "✅ " if word_id in selected_ids else "➕ "
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{prefix}{label}",
                    callback_data=f"pron:select:toggle:{word_id}:{context}:{page}",
                )
            ]
        )

    nav_row: list[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"pron:select:{context}:page:{page-1}")
        )
    nav_row.append(
        InlineKeyboardButton(
            text=f"✅ Tanlanganlar ({selected_count})", callback_data="pron:select:view"
        )
    )
    if has_next:
        nav_row.append(
            InlineKeyboardButton(text="➡️ Keyingi", callback_data=f"pron:select:{context}:page:{page+1}")
        )
    rows.append(nav_row)
    rows.append([InlineKeyboardButton(text="▶️ Quizni boshlash", callback_data="pron:select:start")])
    rows.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="pron:select:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
