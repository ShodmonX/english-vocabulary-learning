from __future__ import annotations

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message

from app.config import settings


class AdminCleanupMiddleware(BaseMiddleware):
    _ADMIN_COMMAND_PREFIXES: tuple[str, ...] = ("/admin", "/addcredit", "/addadmin")

    @staticmethod
    def _is_admin_user(user_id: int | None) -> bool:
        return bool(user_id and user_id in settings.admin_user_ids)

    @staticmethod
    def _is_admin_confirm_callback(data: str | None) -> bool:
        if not data:
            return False
        if data.startswith("admin:"):
            tokens = data.split(":")
            return any(token == "cancel" or token.startswith("confirm") for token in tokens)
        return False

    @staticmethod
    async def _is_admin_state(data: dict) -> bool:
        state = data.get("state")
        if not state:
            return False
        try:
            state_name = await state.get_state()
        except Exception:
            return False
        return bool(state_name and state_name.startswith("AdminStates:"))

    @staticmethod
    async def _delete_message_safe(message: Message | None) -> None:
        if not message:
            return
        try:
            await message.delete()
        except TelegramBadRequest:
            pass

    async def __call__(self, handler, event, data):
        result = await handler(event, data)

        if isinstance(event, Message):
            if self._is_admin_user(event.from_user.id if event.from_user else None):
                text = (event.text or "").strip()
                is_admin_command = any(
                    text.startswith(prefix) for prefix in self._ADMIN_COMMAND_PREFIXES
                )
                if is_admin_command or await self._is_admin_state(data):
                    await self._delete_message_safe(event)
            return result

        if isinstance(event, CallbackQuery):
            if self._is_admin_user(event.from_user.id if event.from_user else None):
                if self._is_admin_confirm_callback(event.data):
                    await self._delete_message_safe(event.message)
            return result

        return result
