from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b


def pronunciation_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("pron.menu_single"), callback_data="pron:menu:single")],
            [InlineKeyboardButton(text=b("pron.menu_quiz"), callback_data="pron:menu:quiz")],
            [InlineKeyboardButton(text=b("pron.menu_select"), callback_data="pron:menu:select")],
        ]
    )


def single_mode_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("pron.recent"), callback_data="pron:single:recent")],
            [InlineKeyboardButton(text=b("pron.search"), callback_data="pron:single:search")],
            [InlineKeyboardButton(text=b("common.back"), callback_data="pron:menu:back")],
        ]
    )


def results_kb(items: list[tuple[int, str]], page: int, context: str, has_next: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for word_id, label in items:
        rows.append([InlineKeyboardButton(text=label, callback_data=f"pron:pick:{word_id}:{context}:{page}")])

    nav_row: list[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(text=b("common.prev_page"), callback_data=f"pron:{context}:page:{page-1}")
        )
    nav_row.append(InlineKeyboardButton(text=b("pron.menu"), callback_data="pron:menu"))
    if has_next:
        nav_row.append(
            InlineKeyboardButton(text=b("pron.next"), callback_data=f"pron:{context}:page:{page+1}")
        )
    rows.append(nav_row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def single_word_kb(context: str, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("pron.other_word"), callback_data=f"pron:single:choose:{context}:{page}")],
            [InlineKeyboardButton(text=b("common.back"), callback_data=f"pron:back:{context}:{page}")],
            [InlineKeyboardButton(text=b("pron.exit"), callback_data="pron:exit")],
        ]
    )


def single_result_kb(context: str, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("pron.retry"), callback_data=f"pron:retry:{context}:{page}")],
            [InlineKeyboardButton(text=b("pron.other_word_list"), callback_data=f"pron:single:choose:{context}:{page}")],
            [InlineKeyboardButton(text=b("pron.exit"), callback_data="pron:exit")],
        ]
    )


def quiz_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=b("pron.quiz_stop"), callback_data="pron:quiz:stop")]]
    )


def quiz_done_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("pron.quiz_again"), callback_data="pron:menu:quiz")],
            [InlineKeyboardButton(text=b("pron.exit"), callback_data="pron:exit")],
        ]
    )


def select_menu_kb(selected_count: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("pron.recent"), callback_data="pron:select:recent")],
            [InlineKeyboardButton(text=b("pron.search"), callback_data="pron:select:search")],
            [
                InlineKeyboardButton(
                    text=b("pron.selected", count=selected_count), callback_data="pron:select:view"
                )
            ],
            [InlineKeyboardButton(text=b("pron.quiz_start"), callback_data="pron:select:start")],
            [InlineKeyboardButton(text=b("common.back"), callback_data="pron:menu:back")],
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
        prefix = b("pron.selected_prefix") if word_id in selected_ids else b("pron.add_prefix")
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
            InlineKeyboardButton(text=b("common.prev_page"), callback_data=f"pron:select:{context}:page:{page-1}")
        )
    nav_row.append(
        InlineKeyboardButton(
            text=b("pron.selected", count=selected_count), callback_data="pron:select:view"
        )
    )
    if has_next:
        nav_row.append(
            InlineKeyboardButton(text=b("pron.next"), callback_data=f"pron:select:{context}:page:{page+1}")
        )
    rows.append(nav_row)
    rows.append([InlineKeyboardButton(text=b("pron.quiz_start"), callback_data="pron:select:start")])
    rows.append([InlineKeyboardButton(text=b("common.back"), callback_data="pron:select:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
