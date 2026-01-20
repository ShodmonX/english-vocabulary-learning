from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from aiogram.exceptions import TelegramBadRequest

from app.bot.handlers.leaderboard.menu import _edit_or_send
from app.bot.keyboards.leaderboard.settings import leaderboard_settings_kb
from app.db.repo.public_profile import (
    get_or_create_profile,
    set_opt_in,
    set_public_name,
    set_show_username,
)
from app.db.repo.users import get_or_create_user
from app.db.session import AsyncSessionLocal
from app.services.i18n import t

router = Router()


class LeaderboardSettingsStates(StatesGroup):
    alias_input = State()


def _settings_text(profile) -> str:
    name = profile.public_name or t("common.none")
    opt = t("common.status_on") if profile.leaderboard_opt_in else t("common.status_off")
    username = t("common.status_on") if profile.show_username else t("common.status_off")
    return t(
        "leaderboard.settings_body",
        opt=opt,
        name=name,
        username=username,
    )


@router.callback_query(F.data == "lb:settings")
async def leaderboard_settings(callback: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        profile = await get_or_create_profile(session, user.id)
    await _edit_or_send(
        callback.message,
        state,
        _settings_text(profile),
        reply_markup=leaderboard_settings_kb(
            profile.leaderboard_opt_in, profile.show_username
        ),
    )
    await callback.answer()


@router.callback_query(F.data == "lb:settings:optin")
async def leaderboard_toggle_optin(callback: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        profile = await get_or_create_profile(session, user.id)
        await set_opt_in(session, user.id, not profile.leaderboard_opt_in)
        profile = await get_or_create_profile(session, user.id)
    await _edit_or_send(
        callback.message,
        state,
        _settings_text(profile),
        reply_markup=leaderboard_settings_kb(
            profile.leaderboard_opt_in, profile.show_username
        ),
    )
    await callback.answer()


@router.callback_query(F.data == "lb:settings:username")
async def leaderboard_toggle_username(callback: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id)
        profile = await get_or_create_profile(session, user.id)
        await set_show_username(session, user.id, not profile.show_username)
        profile = await get_or_create_profile(session, user.id)
    await _edit_or_send(
        callback.message,
        state,
        _settings_text(profile),
        reply_markup=leaderboard_settings_kb(
            profile.leaderboard_opt_in, profile.show_username
        ),
    )
    await callback.answer()


@router.callback_query(F.data == "lb:settings:alias")
async def leaderboard_alias_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(LeaderboardSettingsStates.alias_input)
    await _edit_or_send(
        callback.message,
        state,
        t("leaderboard.alias_prompt"),
    )
    await callback.answer()


@router.message(LeaderboardSettingsStates.alias_input)
async def leaderboard_alias_save(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text:
        await message.answer(t("leaderboard.alias_empty"))
        return
    alias = None if text == "-" else text[:64]
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, message.from_user.id)
        await get_or_create_profile(session, user.id)
        await set_public_name(session, user.id, alias)
        profile = await get_or_create_profile(session, user.id)
    await state.set_state(None)
    await _edit_or_send(
        message,
        state,
        _settings_text(profile),
        reply_markup=leaderboard_settings_kb(
            profile.leaderboard_opt_in, profile.show_username
        ),
    )
    try:
        await message.delete()
    except TelegramBadRequest:
        pass
