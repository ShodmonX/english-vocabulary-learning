from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b


def credits_buy_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("credits.buy_limit"), callback_data="credits:topup")]
        ]
    )


def credits_topup_methods_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=b("profile.topup_admin"), callback_data="profile:topup:admin"
                ),
                InlineKeyboardButton(
                    text=b("profile.topup_stars"), callback_data="profile:topup:stars"
                ),
            ]
        ]
    )
