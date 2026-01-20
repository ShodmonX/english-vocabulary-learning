from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.main import main_menu_kb
from app.config import settings
from app.bot.keyboards.settings import settings_main_kb
from app.bot.handlers.settings.states import SettingsStates
from app.db.repo.user_settings import get_or_create_user_settings
from app.db.repo.users import get_or_create_user, get_user_by_telegram_id
from app.db.session import AsyncSessionLocal
from app.services.i18n import t

router = Router()


def _menu_text(settings) -> str:
    notifications = t("common.status_on") if settings.notifications_enabled else t("common.status_off")
    auto_translation = (
        t("common.status_on") if settings.auto_translation_suggest else t("common.status_off")
    )
    pronunciation = t("common.status_on") if settings.pronunciation_enabled else t("common.status_off")
    return t(
        "settings.menu_body",
        daily_goal=settings.learning_words_per_day,
        quiz_size=settings.quiz_words_per_session,
        pronunciation=pronunciation,
        auto_translation=auto_translation,
        notifications=notifications,
    )


async def open_settings_message(
    message: Message, user_id: int, state: FSMContext
) -> None:
    await state.clear()
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, user_id)
        if not user:
            await message.answer(t("common.start_required"))
            return
        settings = await get_or_create_user_settings(session, user)
    await state.set_state(SettingsStates.menu)
    await message.answer(_menu_text(settings), reply_markup=settings_main_kb())


@router.callback_query(F.data == "menu:settings")
async def open_settings(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_reply_markup(reply_markup=None)
    await open_settings_message(callback.message, callback.from_user.id, state)
    await callback.answer()


@router.callback_query(F.data == "settings:menu")
async def settings_menu(callback: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer(t("common.start_required"))
            await state.clear()
            return
        settings = await get_or_create_user_settings(session, user)
    await state.set_state(SettingsStates.menu)
    await callback.message.edit_text(_menu_text(settings), reply_markup=settings_main_kb())
    await callback.answer()


@router.callback_query(F.data == "settings:back")
async def settings_back(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(t("common.back_main_menu"))
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
