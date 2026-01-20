from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.leaderboard.main import leaderboard_menu_kb
from app.bot.keyboards.main import main_menu_kb
from app.db.repo.public_profile import get_or_create_profile
from app.db.repo.users import get_or_create_user
from app.db.session import AsyncSessionLocal
from app.config import settings
from app.services.i18n import t

router = Router()

async def _edit_or_send(
    message: Message,
    state: FSMContext,
    text: str,
    reply_markup=None,
) -> None:
    data = await state.get_data()
    message_id = data.get("leader_message_id")
    if message_id:
        try:
            await message.bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
            )
            return
        except Exception:
            pass
    sent = await message.answer(text, reply_markup=reply_markup)
    await state.update_data(leader_message_id=sent.message_id)


async def open_leaderboard_menu(message: Message, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, message.from_user.id)
        profile = await get_or_create_profile(session, user.id)
    note = t("leaderboard.menu_note") if not profile.leaderboard_opt_in else ""
    await _edit_or_send(
        message,
        state,
        f"{t('leaderboard.menu_title')}{note}",
        reply_markup=leaderboard_menu_kb(),
    )


@router.callback_query(F.data == "lb:menu")
async def leaderboard_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await open_leaderboard_menu(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "lb:exit")
async def leaderboard_exit(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(leader_message_id=None)
    await callback.message.edit_text(t("leaderboard.closed"))
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        streak = user.current_streak
    await callback.message.answer(
        t("common.main_menu"),
        reply_markup=main_menu_kb(
            is_admin=callback.from_user.id in settings.admin_user_ids, streak=streak
        ),
    )
    await callback.answer()
