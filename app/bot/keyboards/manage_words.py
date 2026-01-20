from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b


def manage_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("manage.search"), callback_data="manage:search")],
            [InlineKeyboardButton(text=b("manage.recent"), callback_data="manage:recent")],
        ]
    )


def results_kb(
    items: list[tuple[int, str]], page: int, context: str, has_next: bool
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for word_id, label in items:
        rows.append(
            [InlineKeyboardButton(text=label, callback_data=f"word:open:{word_id}:{context}:{page}")]
        )

    nav_row: list[InlineKeyboardButton] = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(text=b("common.prev_page"), callback_data=f"manage:{context}:page:{page-1}")
        )
    nav_row.append(InlineKeyboardButton(text=b("manage.menu"), callback_data="manage:menu"))
    if has_next:
        nav_row.append(
            InlineKeyboardButton(
                text=b("manage.next"), callback_data=f"manage:{context}:page:{page+1}"
            )
        )
    rows.append(nav_row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def word_detail_kb(word_id: int, context: str, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("manage.edit"), callback_data=f"word:edit:{word_id}:{context}:{page}")],
            [InlineKeyboardButton(text=b("manage.delete"), callback_data=f"word:delete:{word_id}:{context}:{page}")],
            [InlineKeyboardButton(text=b("common.back"), callback_data=f"word:back:{context}:{page}")],
        ]
    )


def delete_confirm_kb(word_id: int, context: str, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("manage.delete_confirm"), callback_data=f"word:delete_confirm:{word_id}:{context}:{page}")],
            [InlineKeyboardButton(text=b("manage.cancel"), callback_data=f"word:open:{word_id}:{context}:{page}")],
        ]
    )


def edit_menu_kb(word_id: int, context: str, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("manage.field_word"), callback_data=f"word:edit_field:word:{word_id}:{context}:{page}")],
            [InlineKeyboardButton(text=b("manage.field_translation"), callback_data=f"word:edit_field:translation:{word_id}:{context}:{page}")],
            [InlineKeyboardButton(text=b("manage.field_example"), callback_data=f"word:edit_field:example:{word_id}:{context}:{page}")],
            [InlineKeyboardButton(text=b("manage.cancel"), callback_data=f"word:open:{word_id}:{context}:{page}")],
        ]
    )


def translation_warning_kb(word_id: int, context: str, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("manage.translation_force"), callback_data=f"word:translation_force:{word_id}:{context}:{page}")],
            [InlineKeyboardButton(text=b("manage.translation_retry"), callback_data=f"word:translation_retry:{word_id}:{context}:{page}")],
        ]
    )


def example_skip_kb(word_id: int, context: str, page: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("manage.example_skip"), callback_data=f"word:example_skip:{word_id}:{context}:{page}")]
        ]
    )
