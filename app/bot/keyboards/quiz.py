from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b


def quiz_options_kb(options: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    labels = ["A", "B", "C", "D"]
    for index, (word_id, word) in enumerate(options, start=1):
        label = labels[index - 1] if index <= 4 else str(index)
        row.append(
            InlineKeyboardButton(
                text=f"{label}) {word}", callback_data=f"quiz:answer:{word_id}"
            )
        )
        if index % 2 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text=b("quiz.exit"), callback_data="quiz:exit")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def quiz_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("quiz.menu_last"), callback_data="quiz:menu:last")],
            [InlineKeyboardButton(text=b("quiz.menu_selected"), callback_data="quiz:menu:selected")],
        ]
    )
