from datetime import time

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.settings import notifications_kb
from app.bot.handlers.settings.states import SettingsStates
from app.db.repo.user_settings import get_or_create_user_settings, update_user_settings
from app.db.repo.users import get_user_by_telegram_id
from app.db.session import AsyncSessionLocal
from app.services.i18n import t

router = Router()


def _notifications_text(settings) -> str:
    status = t("common.status_on") if settings.notifications_enabled else t("common.status_off")
    time_text = (
        settings.notification_time.strftime("%H:%M")
        if settings.notification_time
        else t("common.none")
    )
    return t("settings.notifications_body", status=status, time=time_text)


def _parse_time(value: str) -> time | None:
    parts = value.strip().split(":")
    if len(parts) != 2:
        return None
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        return None
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    return time(hour, minute)


@router.callback_query(F.data == "settings:notifications")
async def notifications_menu(callback: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer(t("common.start_required"))
            await state.clear()
            return
        settings = await get_or_create_user_settings(session, user)
    await state.set_state(SettingsStates.notifications)
    await callback.message.edit_text(
        _notifications_text(settings), reply_markup=notifications_kb(settings.notifications_enabled)
    )
    await callback.answer()


@router.callback_query(F.data == "settings:notifications:toggle")
async def notifications_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, callback.from_user.id)
        if not user:
            await callback.message.answer(t("common.start_required"))
            await state.clear()
            return
        settings = await get_or_create_user_settings(session, user)
        new_value = not settings.notifications_enabled
        notification_time = settings.notification_time or time(20, 0)
        settings = await update_user_settings(
            session,
            settings.user_id,
            notifications_enabled=new_value,
            notification_time=notification_time,
        )

    from app.main import reminder_service

    if new_value:
        reminder_service.schedule_user(
            callback.from_user.id, notification_time, "Asia/Tashkent"
        )
    else:
        reminder_service.remove_user(callback.from_user.id)

    await state.set_state(SettingsStates.notifications)
    await callback.message.edit_text(
        _notifications_text(settings), reply_markup=notifications_kb(settings.notifications_enabled)
    )
    await callback.message.answer(t("common.saved"))
    await callback.answer()


@router.callback_query(F.data == "settings:reminder_toggle")
async def legacy_reminder_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    await notifications_toggle(callback, state)


@router.callback_query(F.data == "settings:notifications:time")
async def notifications_time(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SettingsStates.notifications_time)
    await callback.message.answer(t("settings.notifications_time_prompt"))
    await callback.answer()


@router.callback_query(F.data == "settings:reminder_time")
async def legacy_reminder_time(callback: CallbackQuery, state: FSMContext) -> None:
    await notifications_time(callback, state)


@router.message(SettingsStates.notifications_time)
async def save_notifications_time(message: Message, state: FSMContext) -> None:
    parsed = _parse_time(message.text)
    if not parsed:
        await message.answer(t("settings.notifications_time_invalid"))
        return

    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            await message.answer(t("common.start_required"))
            await state.clear()
            return
        settings = await get_or_create_user_settings(session, user)
        settings = await update_user_settings(
            session, settings.user_id, notification_time=parsed
        )

    from app.main import reminder_service

    if settings.notifications_enabled:
        reminder_service.schedule_user(message.from_user.id, parsed, "Asia/Tashkent")

    await state.set_state(SettingsStates.notifications)
    await message.answer(t("common.saved"))
    await message.answer(
        _notifications_text(settings), reply_markup=notifications_kb(settings.notifications_enabled)
    )


@router.callback_query(F.data == "settings:notifications:reset")
async def notifications_reset(callback: CallbackQuery, state: FSMContext) -> None:
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
            notifications_enabled=False,
            notification_time=time(20, 0),
        )

    from app.main import reminder_service

    reminder_service.remove_user(callback.from_user.id)

    await state.set_state(SettingsStates.notifications)
    await callback.message.edit_text(
        _notifications_text(settings), reply_markup=notifications_kb(settings.notifications_enabled)
    )
    await callback.message.answer(t("common.saved"))
    await callback.answer()
