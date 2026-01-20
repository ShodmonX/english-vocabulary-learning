from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b


def practice_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("practice.quick"), callback_data="practice:mode:quick")],
            [InlineKeyboardButton(text=b("practice.recall"), callback_data="practice:mode:recall")],
            [InlineKeyboardButton(text=b("common.back"), callback_data="practice:exit")],
        ]
    )


def practice_quick_step_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=b("practice.show_meaning"), callback_data="practice:quick:show"),
                InlineKeyboardButton(text=b("practice.skip"), callback_data="practice:quick:skip"),
            ],
            [InlineKeyboardButton(text=b("practice.stop"), callback_data="practice:stop")],
        ]
    )


def practice_quick_rate_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=b("practice.rate_again"), callback_data="practice:rate:again"),
                InlineKeyboardButton(text=b("practice.rate_hard"), callback_data="practice:rate:hard"),
            ],
            [
                InlineKeyboardButton(text=b("practice.rate_good"), callback_data="practice:rate:good"),
                InlineKeyboardButton(text=b("practice.rate_easy"), callback_data="practice:rate:easy"),
            ],
            [InlineKeyboardButton(text=b("practice.stop"), callback_data="practice:stop")],
        ]
    )


def practice_recall_prompt_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("practice.skip"), callback_data="practice:recall:skip")],
            [InlineKeyboardButton(text=b("practice.stop"), callback_data="practice:stop")],
        ]
    )


def practice_summary_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("practice.again"), callback_data="practice:again")],
            [InlineKeyboardButton(text=b("practice.change_mode"), callback_data="practice:menu")],
            [InlineKeyboardButton(text=b("practice.menu"), callback_data="practice:exit")],
        ]
    )


def practice_due_empty_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("practice.due_new"), callback_data="practice:due:new")],
            [InlineKeyboardButton(text=b("practice.menu_back"), callback_data="practice:due:exit")],
        ]
    )
