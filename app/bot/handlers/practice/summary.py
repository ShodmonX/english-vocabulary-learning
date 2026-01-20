from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.practice import practice_summary_kb
from app.bot.handlers.practice.common import edit_or_send
from app.db.repo.sessions import delete_session
from app.db.repo.users import get_or_create_user
from app.db.session import AsyncSessionLocal
from app.bot.handlers.practice.states import PracticeStates
from app.services.i18n import t

router = Router()


def _summary_text(stats: dict[str, int], streak: int, longest: int) -> str:
    text = t(
        "practice.summary_body",
        again=stats.get("again", 0),
        hard=stats.get("hard", 0),
        good=stats.get("good", 0),
        easy=stats.get("easy", 0),
    )
    if streak >= 2:
        text += t("practice.summary_streak", streak=streak)
    if longest >= 2 and streak == longest:
        text += t("practice.summary_record", longest=longest)
    return text


async def show_summary(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await state.set_state(PracticeStates.done)
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, message.from_user.id)
        await delete_session(session, user.id)
        streak = user.current_streak
        longest = user.longest_streak
    await edit_or_send(
        message,
        state,
        _summary_text(data.get("stats", {}), streak, longest),
        reply_markup=practice_summary_kb(),
        parse_mode=None,
    )


@router.callback_query(F.data == "practice:again")
async def practice_again(callback: CallbackQuery, state: FSMContext) -> None:
    from app.bot.handlers.practice.menu import _start_mode

    await callback.message.edit_reply_markup(reply_markup=None)
    await _start_mode(callback.message, state, "quick", callback.from_user.id)
    await callback.answer()
