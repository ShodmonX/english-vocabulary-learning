from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.handlers.admin.common import ensure_admin_callback
from app.bot.keyboards.admin.main import admin_back_kb
from app.db.repo.admin import get_admin_stats
from app.db.session import AsyncSessionLocal

router = Router()


@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    async with AsyncSessionLocal() as session:
        stats = await get_admin_stats(session)
    text = (
        "📊 Umumiy statistika:\n"
        f"👥 Jami userlar: {stats['total_users']}\n"
        f"📘 Jami so‘zlar: {stats['total_words']}\n"
        f"🧠 Bugun due: {stats['due_words']}\n"
        f"🧩 Bugungi quiz sessiyalar: {stats['quiz_sessions_today']}\n"
        f"🗣 Bugungi talaffuz testlar: {stats['pronunciation_today']}\n"
        f"⏱ Oxirgi 24 soat activity: {stats['activity_24h']}"
    )
    await callback.message.edit_text(text, reply_markup=admin_back_kb())
    await callback.answer()
