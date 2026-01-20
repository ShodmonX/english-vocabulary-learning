from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.settings import learning_kb
from app.bot.handlers.settings.states import SettingsStates
from app.db.repo.user_settings import get_or_create_user_settings, update_user_settings
from app.db.repo.users import get_user_by_telegram_id
from app.db.session import AsyncSessionLocal
from app.services.i18n import t

router = Router()


def _learning_text(settings) -> str:
    return t(
        "settings.learning_body",
        daily_goal=settings.learning_words_per_day,
    )


@router.callback_query(F.data == "settings:learning")
async def learning_menu(callback: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer(t("common.start_required"))
            await state.clear()
            return
        settings = await get_or_create_user_settings(session, user)
    await state.set_state(SettingsStates.learning)
    await callback.message.edit_text(_learning_text(settings), reply_markup=learning_kb())
    await callback.answer()


@router.callback_query(F.data == "settings:learning:srs")
async def learning_srs_placeholder(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.answer(t("settings.learning_srs_notice"))
    await callback.answer()


@router.callback_query(F.data == "settings:learning:words_per_day")
async def learning_words_per_day(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SettingsStates.learning_words_per_day)
    await callback.message.answer(t("settings.learning_words_prompt"))
    await callback.answer()


@router.callback_query(F.data == "settings:daily_goal")
async def legacy_daily_goal(callback: CallbackQuery, state: FSMContext) -> None:
    await learning_words_per_day(callback, state)


@router.message(SettingsStates.learning_words_per_day)
async def save_learning_words_per_day(message: Message, state: FSMContext) -> None:
    try:
        value = int(message.text.strip())
    except ValueError:
        await message.answer(t("common.invalid_value"))
        return
    if value < 5 or value > 100:
        await message.answer(t("settings.learning_range"))
        return

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer(t("common.start_required"))
            await state.clear()
            return
        settings = await get_or_create_user_settings(session, user)
        settings = await update_user_settings(
            session, settings.user_id, learning_words_per_day=value
        )

    await state.set_state(SettingsStates.learning)
    await message.answer(t("common.saved"))
    await message.answer(_learning_text(settings), reply_markup=learning_kb())


@router.callback_query(F.data == "settings:learning:reset")
async def learning_reset(callback: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer(t("common.start_required"))
            await state.clear()
            return
        settings = await get_or_create_user_settings(session, user)
        settings = await update_user_settings(
            session, settings.user_id, learning_words_per_day=10
        )
    await state.set_state(SettingsStates.learning)
    await callback.message.edit_text(_learning_text(settings), reply_markup=learning_kb())
    await callback.message.answer(t("common.saved"))
    await callback.answer()
