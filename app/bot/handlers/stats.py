from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.bot.keyboards.main import main_menu_kb
from app.db.repo.stats import get_due_count, get_today_review_stats, get_total_words
from app.db.repo.users import get_user_by_telegram_id
from app.db.session import AsyncSessionLocal

router = Router()


@router.callback_query(F.data == "menu:stats")
async def show_stats(callback: CallbackQuery) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer("Avval /start buyrug‘ini bosing.")
            await callback.answer()
            return

        today_stats = await get_today_review_stats(session, user.id)
        total_words = await get_total_words(session, user.id)
        due_count = await get_due_count(session, user.id)

    text = (
        "Bugungi statistika:\n"
        f"Bilardim: {today_stats['known']}\n"
        f"Unutdim: {today_stats['forgot']}\n"
        f"O‘tkazib yuborildi: {today_stats['skip']}\n\n"
        f"Jami so‘zlar: {total_words}\n"
        f"Due so‘zlar: {due_count}"
    )
    await callback.message.answer(text, reply_markup=main_menu_kb())
    await callback.answer()
