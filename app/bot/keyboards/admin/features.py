from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b


def admin_features_kb(flags: dict[str, bool]) -> InlineKeyboardMarkup:
    def _label(name_key: str, enabled: bool) -> str:
        status = b("admin_features.status_on") if enabled else b("admin_features.status_off")
        return b("admin_features.label", name=b(name_key), status=status)

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=_label("admin_features.quiz", flags.get("quiz", True)), callback_data="admin:features:quiz")],
            [InlineKeyboardButton(text=_label("admin_features.pronunciation", flags.get("pronunciation", True)), callback_data="admin:features:pronunciation")],
            [InlineKeyboardButton(text=_label("admin_features.practice", flags.get("practice", True)), callback_data="admin:features:practice")],
            [InlineKeyboardButton(text=_label("admin_features.translation", flags.get("translation", True)), callback_data="admin:features:translation")],
            [InlineKeyboardButton(text=b("common.back"), callback_data="admin:menu")],
        ]
    )
