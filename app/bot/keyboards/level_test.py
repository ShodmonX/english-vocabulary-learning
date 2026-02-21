from __future__ import annotations

from typing import Sequence

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.level_test import UI_MODE_FLAGGED
from app.services.i18n import b


def level_test_entry_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("level_test.quick"), callback_data="lt:start:quick")],
            [InlineKeyboardButton(text=b("level_test.full"), callback_data="lt:start:full")],
        ]
    )


def level_test_stop_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=b("common.confirm_yes"), callback_data="lt:stop:yes"),
                InlineKeyboardButton(text=b("common.confirm_no"), callback_data="lt:stop:no"),
            ]
        ]
    )


def level_test_summary_kb(next_stage: str | None = None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if next_stage:
        rows.append(
            [
                InlineKeyboardButton(
                    text=b("level_test.start_stage", level=next_stage),
                    callback_data=f"lt:next:{next_stage}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text=b("level_test.retry"), callback_data="lt:retry")])
    rows.append([InlineKeyboardButton(text=b("common.back_main_menu"), callback_data="lt:menu:main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def level_test_question_kb(
    *,
    ui_mode: str,
    current_index: int,
    is_flagged: bool,
    is_answered: bool,
    choices: Sequence[str] | None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if choices:
        for option_index, option_text in enumerate(choices):
            rows.append(
                [
                    InlineKeyboardButton(
                        text=f"{chr(65 + option_index)}) {option_text}",
                        callback_data=f"lt:ans:{current_index}:{option_index}",
                    )
                ]
            )

    if ui_mode == UI_MODE_FLAGGED:
        rows.append(
            [
                InlineKeyboardButton(text=b("level_test.prev_flag"), callback_data="lt:nav:back"),
                InlineKeyboardButton(text=b("level_test.next_flag"), callback_data="lt:nav:next"),
            ]
        )
        rows.append(
            [
                InlineKeyboardButton(
                    text=b("level_test.unflag") if is_flagged else b("level_test.flag"),
                    callback_data="lt:flag",
                ),
                InlineKeyboardButton(text=b("level_test.finish"), callback_data="lt:finish"),
            ]
        )
        return InlineKeyboardMarkup(inline_keyboard=rows)

    rows.append(
        [
            InlineKeyboardButton(text=b("level_test.back"), callback_data="lt:nav:back"),
            InlineKeyboardButton(text=b("level_test.next"), callback_data="lt:nav:next"),
        ]
    )
    rows.append(
        [
            InlineKeyboardButton(
                text=b("level_test.unflag") if is_flagged else b("level_test.flag"),
                callback_data="lt:flag",
            ),
            InlineKeyboardButton(text=b("level_test.stop"), callback_data="lt:stop"),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
