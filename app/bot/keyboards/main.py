from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from app.services.i18n import b


def main_menu_kb(is_admin: bool = False, streak: int | None = None) -> ReplyKeyboardMarkup:
    keyboard = [
        [
            KeyboardButton(text=b("menu.add_word")),
            KeyboardButton(text=b("menu.my_words")),
        ],
        [
            KeyboardButton(text=b("menu.pronunciation")),
            KeyboardButton(text=b("menu.quiz")),
        ],
        [
            KeyboardButton(text=b("menu.practice")),
            KeyboardButton(text=b("menu.stats")),
        ],
        [
            KeyboardButton(text=b("menu.leaderboards")),
            KeyboardButton(text=b("menu.profile")),
        ],
        [
            KeyboardButton(text=b("menu.settings")),
        ],
    ]
    if is_admin:
        keyboard.append([KeyboardButton(text=b("menu.admin"))])
    if streak and streak > 0:
        keyboard.append([KeyboardButton(text=b("menu.streak", days=streak))])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def settings_kb(reminder_enabled: bool = True) -> InlineKeyboardMarkup:
    reminder_label = (
        b("settings.reminder_on") if reminder_enabled else b("settings.reminder_off")
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("settings.daily_goal"), callback_data="settings:daily_goal")],
            [InlineKeyboardButton(text=b("settings.reminder_time"), callback_data="settings:reminder_time")],
            [InlineKeyboardButton(text=reminder_label, callback_data="settings:reminder_toggle")],
            [InlineKeyboardButton(text=b("common.back"), callback_data="settings:back")],
        ]
    )
