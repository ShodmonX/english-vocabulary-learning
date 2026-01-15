from aiogram.types import CallbackQuery, Message

from app.config import settings


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_user_ids


async def ensure_admin_message(message: Message) -> bool:
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Sizda admin huquqi yo‘q.")
        return False
    return True


async def ensure_admin_callback(callback: CallbackQuery) -> bool:
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ Sizda admin huquqi yo‘q.", show_alert=True)
        return False
    return True


def parse_int(value: str) -> int | None:
    try:
        return int(value.strip())
    except (TypeError, ValueError):
        return None
