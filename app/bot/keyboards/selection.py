from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b


def selection_menu_kb(purpose: str, selected_count: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=b("selection.recent"),
                    callback_data=f"select:{purpose}:recent",
                )
            ],
            [
                InlineKeyboardButton(
                    text=b("selection.search"),
                    callback_data=f"select:{purpose}:search",
                )
            ],
            [
                InlineKeyboardButton(
                    text=b("selection.selected", count=selected_count),
                    callback_data=f"select:{purpose}:view",
                )
            ],
            [
                InlineKeyboardButton(
                    text=b("selection.clear"),
                    callback_data=f"select:{purpose}:clear",
                )
            ],
            [
                InlineKeyboardButton(
                    text=b("selection.confirm"),
                    callback_data=f"select:{purpose}:confirm",
                )
            ],
            [
                InlineKeyboardButton(
                    text=b("selection.back"),
                    callback_data=f"select:{purpose}:back",
                )
            ],
        ]
    )


def selection_results_kb(
    items: list[tuple[int, str]],
    selected_ids: set[int],
    *,
    purpose: str,
    context: str,
    page: int,
    has_next: bool,
    selected_count: int,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for word_id, label in items:
        prefix = (
            b("selection.selected_prefix")
            if word_id in selected_ids
            else b("selection.add_prefix")
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{prefix}{label}",
                    callback_data=f"select:{purpose}:toggle:{word_id}:{context}:{page}",
                )
            ]
        )

    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                text=b("common.prev_page"),
                callback_data=f"select:{purpose}:page:{context}:{page - 1}",
            )
        )
    nav.append(
        InlineKeyboardButton(
            text=b("selection.menu"),
            callback_data=f"select:{purpose}:menu",
        )
    )
    if has_next:
        nav.append(
            InlineKeyboardButton(
                text=b("common.next_page"),
                callback_data=f"select:{purpose}:page:{context}:{page + 1}",
            )
        )
    rows.append(nav)
    rows.append(
        [
            InlineKeyboardButton(
                text=b("selection.confirm"),
                callback_data=f"select:{purpose}:confirm",
            )
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text=b("selection.selected", count=selected_count),
                callback_data=f"select:{purpose}:view",
            ),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
