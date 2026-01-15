from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.repo.users import get_user_by_telegram_id
from app.db.session import AsyncSessionLocal


class BlockedUserMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if not user_id:
            return await handler(event, data)
        if user_id in settings.admin_user_ids:
            return await handler(event, data)

        async with AsyncSessionLocal() as session:
            user = await get_user_by_telegram_id(session, user_id)
            if user and user.is_blocked:
                text = "⛔ Siz bloklangansiz. Admin bilan bog‘laning."
                if isinstance(event, CallbackQuery):
                    await event.answer(text, show_alert=True)
                else:
                    await event.answer(text)
                return

        return await handler(event, data)
