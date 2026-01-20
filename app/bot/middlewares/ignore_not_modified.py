from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramBadRequest


class IgnoreNotModifiedMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        try:
            return await handler(event, data)
        except TelegramBadRequest as exc:
            message = str(exc)
            if "message is not modified" in message:
                return None
            if "query is too old" in message or "query ID is invalid" in message:
                return None
            raise
