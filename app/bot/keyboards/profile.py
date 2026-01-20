from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b


def profile_refresh_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("profile.refresh"), callback_data="profile:refresh")],
            [
                InlineKeyboardButton(
                    text=b("profile.topup_admin"), callback_data="profile:topup:admin"
                ),
                InlineKeyboardButton(
                    text=b("profile.topup_stars"), callback_data="profile:topup:stars"
                ),
            ],
        ]
    )


def profile_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=b("profile.back"), callback_data="profile:refresh")]]
    )


def stars_packages_kb(package_keys: list[str]) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(
            text=b("profile.stars_package", package_key=key),
            callback_data=f"profile:stars:{key.lower()}",
        )
        for key in package_keys
    ]
    rows = [buttons[i : i + 3] for i in range(0, len(buttons), 3)]
    rows.append([InlineKeyboardButton(text=b("profile.back"), callback_data="profile:refresh")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
