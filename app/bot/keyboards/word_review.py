from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b

REVIEW_PAGE_SIZE = 10


def word_review_kb(*, offset: int, total: int, word_id: int) -> InlineKeyboardMarkup:
    page = offset // REVIEW_PAGE_SIZE
    detail_callback = f"word:open:{word_id}:recent:{page}"
    if total <= 1:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=b("word_review.detail"),
                        callback_data=detail_callback,
                    )
                ]
            ]
        )

    prev_callback = f"wr:nav:{offset-1}" if offset > 0 else "wr:noop"
    next_callback = f"wr:nav:{offset+1}" if offset < (total - 1) else "wr:noop"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=b("common.prev"), callback_data=prev_callback),
                InlineKeyboardButton(text=b("word_review.detail"), callback_data=detail_callback),
                InlineKeyboardButton(text=b("common.next"), callback_data=next_callback),
            ]
        ]
    )
