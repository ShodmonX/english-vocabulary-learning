from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.settings import pronunciation_mode_kb, tests_kb
from app.bot.handlers.settings.states import SettingsStates
from app.db.repo.user_settings import get_or_create_user_settings, update_user_settings
from app.db.repo.users import get_user_by_telegram_id
from app.db.session import AsyncSessionLocal
from app.services.i18n import t

router = Router()


def _tests_text(settings) -> str:
    pronunciation = t("common.status_on") if settings.pronunciation_enabled else t("common.status_off")
    return t(
        "settings.tests_body",
        quiz_size=settings.quiz_words_per_session,
        pronunciation=pronunciation,
        mode=settings.pronunciation_mode,
    )


@router.callback_query(F.data == "settings:tests")
async def tests_menu(callback: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer(t("common.start_required"))
            await state.clear()
            return
        settings = await get_or_create_user_settings(session, user)
    await state.set_state(SettingsStates.tests)
    await callback.message.edit_text(
        _tests_text(settings), reply_markup=tests_kb(settings.pronunciation_enabled)
    )
    await callback.answer()


@router.callback_query(F.data == "settings:tests:quiz_size")
async def tests_quiz_size(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SettingsStates.tests_quiz_size)
    await callback.message.answer(t("settings.tests_quiz_prompt"))
    await callback.answer()


@router.message(SettingsStates.tests_quiz_size)
async def save_tests_quiz_size(message: Message, state: FSMContext) -> None:
    try:
        value = int(message.text.strip())
    except ValueError:
        await message.answer(t("common.invalid_value"))
        return
    if value < 4 or value > 50:
        await message.answer(t("settings.tests_quiz_range"))
        return

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer(t("common.start_required"))
            await state.clear()
            return
        settings = await get_or_create_user_settings(session, user)
        settings = await update_user_settings(
            session, settings.user_id, quiz_words_per_session=value
        )

    await state.set_state(SettingsStates.tests)
    await message.answer(t("common.saved"))
    await message.answer(
        _tests_text(settings), reply_markup=tests_kb(settings.pronunciation_enabled)
    )


@router.callback_query(F.data == "settings:tests:pronunciation_toggle")
async def tests_pronunciation_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer(t("common.start_required"))
            await state.clear()
            return
        settings = await get_or_create_user_settings(session, user)
        new_value = not settings.pronunciation_enabled
        settings = await update_user_settings(
            session, settings.user_id, pronunciation_enabled=new_value
        )
    await state.set_state(SettingsStates.tests)
    await callback.message.edit_text(
        _tests_text(settings), reply_markup=tests_kb(settings.pronunciation_enabled)
    )
    await callback.message.answer(t("common.saved"))
    await callback.answer()


@router.callback_query(F.data == "settings:tests:pronunciation_mode")
async def tests_pronunciation_mode(callback: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer(t("common.start_required"))
            await state.clear()
            return
        settings = await get_or_create_user_settings(session, user)
    await state.set_state(SettingsStates.tests_pronunciation_mode)
    await callback.message.edit_text(
        t("settings.tests_pron_mode_prompt"),
        reply_markup=pronunciation_mode_kb(settings.pronunciation_mode),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("settings:tests:pronunciation_mode:"))
async def tests_pronunciation_mode_set(callback: CallbackQuery, state: FSMContext) -> None:
    mode = callback.data.split(":")[-1]
    if mode not in {"single", "quiz", "both"}:
        await callback.answer()
        return
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer(t("common.start_required"))
            await state.clear()
            return
        settings = await get_or_create_user_settings(session, user)
        settings = await update_user_settings(
            session, settings.user_id, pronunciation_mode=mode
        )
    await state.set_state(SettingsStates.tests)
    await callback.message.edit_text(
        _tests_text(settings), reply_markup=tests_kb(settings.pronunciation_enabled)
    )
    await callback.message.answer(t("common.saved"))
    await callback.answer()


@router.callback_query(F.data == "settings:tests:reset")
async def tests_reset(callback: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer(t("common.start_required"))
            await state.clear()
            return
        settings = await get_or_create_user_settings(session, user)
        settings = await update_user_settings(
            session,
            settings.user_id,
            quiz_words_per_session=10,
            pronunciation_enabled=True,
            pronunciation_mode="both",
        )
    await state.set_state(SettingsStates.tests)
    await callback.message.edit_text(
        _tests_text(settings), reply_markup=tests_kb(settings.pronunciation_enabled)
    )
    await callback.message.answer(t("common.saved"))
    await callback.answer()
