from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.main import main_menu_kb
from app.config import settings
from app.db.repo.stats import (
    get_due_count,
    get_today_review_stats,
    get_total_words,
    get_weekly_summary,
)
from app.db.repo.users import get_user_by_telegram_id
from app.db.session import AsyncSessionLocal

router = Router()


@router.callback_query(F.data == "menu:stats")
async def show_stats(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_reply_markup(reply_markup=None)
    await show_stats_message(callback.message, callback.from_user.id, state)
    await callback.answer()


async def show_stats_message(
    message: Message, user_id: int, state: FSMContext
) -> None:
    await state.clear()
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, user_id)
        if not user:
            await message.answer("⚠️ Avval /start buyrug‘ini bosing 🙂")
            return

        today_stats = await get_today_review_stats(session, user.id)
        weekly = await get_weekly_summary(session, user.id)
        total_words = await get_total_words(session, user.id)
        due_count = await get_due_count(session, user.id)

    total_today = today_stats["known"] + today_stats["forgot"] + today_stats["skip"]
    accuracy = (today_stats["known"] / total_today * 100) if total_today else 0
    weekly_lines = []
    for item in weekly:
        day_str = item["day"].strftime("%d.%m")
        weekly_lines.append(
            f"{day_str}: {item['total']} (K:{item['known']} F:{item['forgot']} S:{item['skip']})"
        )

    text = (
        "📊 Bugungi natijalar:\n"
        f"Bilganingiz: {today_stats['known']}\n"
        f"Qayta ko‘riladiganlar: {today_stats['forgot']}\n"
        f"O‘tkazib yuborildi: {today_stats['skip']}\n\n"
        f"Jami: {total_today}\n"
        f"Aniqlik: {accuracy:.0f}%\n\n"
        f"Jami so‘zlar: {total_words}\n"
        f"Due so‘zlar: {due_count}\n\n"
        "Oxirgi 7 kun:\n"
        + "\n".join(weekly_lines)
        + "\n\n💡 Davom eting, natija albatta bo‘ladi!"
    )
    await message.answer(
        text,
        reply_markup=main_menu_kb(
            is_admin=user_id in settings.admin_user_ids,
            streak=user.current_streak,
        ),
    )
