from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_features_kb(flags: dict[str, bool]) -> InlineKeyboardMarkup:
    def _label(name: str, enabled: bool) -> str:
        status = "ON ✅" if enabled else "OFF ❌"
        return f"{name}: {status}"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=_label("🧩 Quiz", flags.get("quiz", True)), callback_data="admin:features:quiz")],
            [InlineKeyboardButton(text=_label("🗣 Talaffuz", flags.get("pronunciation", True)), callback_data="admin:features:pronunciation")],
            [InlineKeyboardButton(text=_label("📘 Mashq", flags.get("practice", True)), callback_data="admin:features:practice")],
            [InlineKeyboardButton(text=_label("🌍 Tarjima", flags.get("translation", True)), callback_data="admin:features:translation")],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:menu")],
        ]
    )
