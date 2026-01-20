from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramBadRequest


class IgnoreNotModifiedMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        try:
            return await handler(event, data)
        except TelegramBadRequest as exc:
            if "message is not modified" in str(exc):
                return None
            raise
