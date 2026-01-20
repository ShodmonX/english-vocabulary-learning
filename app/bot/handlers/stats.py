from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.main import main_menu_kb
from app.config import settings
from app.db.repo.stats import (
    get_due_count,
    get_recent_pronunciation_results,
    get_recent_quiz_results,
    get_today_review_stats,
    get_total_words,
    get_weekly_summary,
)
from app.db.repo.users import get_user_by_telegram_id
from app.db.session import AsyncSessionLocal
from app.services.i18n import t

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
            await message.answer(t("common.start_required"))
            return

        today_stats = await get_today_review_stats(session, user.id)
        weekly = await get_weekly_summary(session, user.id)
        total_words = await get_total_words(session, user.id)
        due_count = await get_due_count(session, user.id)
        recent_quiz = await get_recent_quiz_results(session, user.id, limit=3)
        recent_pron = await get_recent_pronunciation_results(session, user.id, limit=3)

    total_today = today_stats["known"] + today_stats["forgot"] + today_stats["skip"]
    accuracy = (today_stats["known"] / total_today * 100) if total_today else 0
    weekly_lines = []
    for item in weekly:
        day_str = item["day"].strftime("%d.%m")
        weekly_lines.append(
            t(
                "stats.weekly_line",
                day=day_str,
                total=item["total"],
                known=item["known"],
                forgot=item["forgot"],
                skip=item["skip"],
            )
        )

    quiz_lines = []
    for item in recent_quiz:
        total = (item.correct or 0) + (item.wrong or 0)
        acc = item.accuracy if item.accuracy is not None else 0
        quiz_lines.append(
            t(
                "stats.quiz_line",
                total=total,
                correct=item.correct or 0,
                wrong=item.wrong or 0,
                accuracy=acc,
            )
        )
    if not quiz_lines:
        quiz_lines.append(t("stats.quiz_none"))

    pron_lines = []
    for item in recent_pron:
        verdict = item.verdict or t("common.none")
        word = item.reference_word or t("common.none")
        pron_lines.append(t("stats.pron_line", word=word, verdict=verdict))
    if not pron_lines:
        pron_lines.append(t("stats.pron_none"))

    text = t(
        "stats.body",
        known=today_stats["known"],
        forgot=today_stats["forgot"],
        skip=today_stats["skip"],
        total_today=total_today,
        accuracy=accuracy,
        total_words=total_words,
        due_count=due_count,
        quiz_lines="\n".join(quiz_lines),
        pron_lines="\n".join(pron_lines),
        weekly_lines="\n".join(weekly_lines),
    )
    await message.answer(
        text,
        reply_markup=main_menu_kb(
            is_admin=user_id in settings.admin_user_ids,
            streak=user.current_streak,
        ),
    )
