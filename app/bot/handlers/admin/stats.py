from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.handlers.admin.common import ensure_admin_callback
from app.bot.keyboards.admin.main import admin_back_kb
from app.db.repo.admin import get_admin_stats
from app.db.session import AsyncSessionLocal
from app.services.i18n import t

router = Router()


@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    async with AsyncSessionLocal() as session:
        stats = await get_admin_stats(session)
    text = t(
        "admin_stats.body",
        total_users=stats["total_users"],
        total_words=stats["total_words"],
        due_words=stats["due_words"],
        quiz_today=stats["quiz_sessions_today"],
        pron_today=stats["pronunciation_today"],
        activity_24h=stats["activity_24h"],
    )
    await callback.message.edit_text(text, reply_markup=admin_back_kb())
    await callback.answer()
