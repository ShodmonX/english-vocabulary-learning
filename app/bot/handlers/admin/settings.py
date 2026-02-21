from __future__ import annotations

from typing import Literal

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.admin.common import (
    ensure_main_admin_callback,
    ensure_main_admin_message,
    parse_int,
)
from app.bot.handlers.admin.entry import open_admin_panel
from app.bot.handlers.admin.states import AdminStates
from app.bot.keyboards.admin.settings import (
    admin_basic_limit_kb,
    admin_full_test_charge_kb,
    admin_test_limits_kb,
)
from app.bot.keyboards.admin.users import admin_confirm_kb
from app.config import settings
from app.db.repo.app_settings import (
    get_basic_monthly_seconds,
    get_full_question_count,
    get_full_test_charge_seconds,
    get_full_time_limit_seconds,
    get_placement_question_count,
    get_placement_time_limit_seconds,
    set_basic_monthly_seconds,
    set_full_question_count,
    set_full_test_charge_seconds,
    set_full_time_limit_seconds,
    set_placement_question_count,
    set_placement_time_limit_seconds,
)
from app.db.session import AsyncSessionLocal
from app.services.i18n import t

router = Router()

MIN_LIMIT = 1
MAX_LIMIT = 100000
MIN_FULL_TEST_CHARGE = 1
MAX_FULL_TEST_CHARGE = 100000
MIN_TEST_QUESTION_COUNT = 2
MAX_TEST_QUESTION_COUNT = 200
MIN_TEST_TIME_SECONDS = 60
MAX_TEST_TIME_SECONDS = 7200

TestLimitKey = Literal["quick_count", "quick_time", "full_count", "full_time"]


async def _current_basic_limit() -> int:
    async with AsyncSessionLocal() as session:
        value = await get_basic_monthly_seconds(session)
    return value if value and value > 0 else settings.basic_monthly_seconds


async def _current_full_test_charge() -> int:
    async with AsyncSessionLocal() as session:
        value = await get_full_test_charge_seconds(session)
    return value if value and value > 0 else settings.full_test_charge_seconds


async def _current_test_limits() -> dict[TestLimitKey, int]:
    async with AsyncSessionLocal() as session:
        quick_count = await get_placement_question_count(session)
        quick_time = await get_placement_time_limit_seconds(session)
        full_count = await get_full_question_count(session)
        full_time = await get_full_time_limit_seconds(session)
    return {
        "quick_count": quick_count if quick_count and quick_count > 0 else settings.placement_question_count,
        "quick_time": quick_time if quick_time and quick_time > 0 else settings.placement_time_limit_seconds,
        "full_count": full_count if full_count and full_count > 0 else settings.full_question_count,
        "full_time": full_time if full_time and full_time > 0 else settings.full_time_limit_seconds,
    }


def _test_limit_label(key: TestLimitKey) -> str:
    if key == "quick_count":
        return t("admin_settings.label_quick_count")
    if key == "quick_time":
        return t("admin_settings.label_quick_time")
    if key == "full_count":
        return t("admin_settings.label_full_count")
    return t("admin_settings.label_full_time")


def _is_test_limit_valid(key: TestLimitKey, value: int | None) -> bool:
    if not value:
        return False
    if key in {"quick_count", "full_count"}:
        return MIN_TEST_QUESTION_COUNT <= value <= MAX_TEST_QUESTION_COUNT
    return MIN_TEST_TIME_SECONDS <= value <= MAX_TEST_TIME_SECONDS


def _test_limit_invalid_message(key: TestLimitKey) -> str:
    if key in {"quick_count", "full_count"}:
        return t(
            "admin_settings.test_limits_invalid_count",
            min=MIN_TEST_QUESTION_COUNT,
            max=MAX_TEST_QUESTION_COUNT,
        )
    return t(
        "admin_settings.test_limits_invalid_time",
        min=MIN_TEST_TIME_SECONDS,
        max=MAX_TEST_TIME_SECONDS,
    )


def _parse_test_limit_key(raw: str | None) -> TestLimitKey | None:
    if raw in {"quick_count", "quick_time", "full_count", "full_time"}:
        return raw
    return None


async def _apply_test_limit(
    key: TestLimitKey,
    *,
    value: int,
    admin_id: int,
) -> None:
    async with AsyncSessionLocal() as session:
        if key == "quick_count":
            await set_placement_question_count(session, value, admin_id)
            settings.placement_question_count = value
            return
        if key == "quick_time":
            await set_placement_time_limit_seconds(session, value, admin_id)
            settings.placement_time_limit_seconds = value
            return
        if key == "full_count":
            await set_full_question_count(session, value, admin_id)
            settings.full_question_count = value
            return
        await set_full_time_limit_seconds(session, value, admin_id)
        settings.full_time_limit_seconds = value


@router.callback_query(F.data == "admin:basic_limit")
async def admin_basic_limit(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_main_admin_callback(callback):
        return
    await state.set_state(AdminStates.menu)
    value = await _current_basic_limit()
    await callback.message.edit_text(
        t("admin_settings.basic_limit_body", value=value),
        reply_markup=admin_basic_limit_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:basic_limit:edit")
async def admin_basic_limit_edit(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_main_admin_callback(callback):
        return
    await state.set_state(AdminStates.basic_limit_edit)
    await callback.message.edit_text(t("admin_settings.basic_limit_prompt"))
    await callback.answer()


@router.message(AdminStates.basic_limit_edit)
async def admin_basic_limit_value(message: Message, state: FSMContext) -> None:
    if not await ensure_main_admin_message(message):
        return
    new_value = parse_int(message.text or "")
    if not new_value or not (MIN_LIMIT <= new_value <= MAX_LIMIT):
        await message.answer(t("admin_settings.basic_limit_invalid"))
        return
    old_value = await _current_basic_limit()
    await state.update_data(basic_limit_new=new_value, basic_limit_old=old_value)
    await message.answer(
        t("admin_settings.basic_limit_confirm", old=old_value, new=new_value),
        reply_markup=admin_confirm_kb(
            "admin:basic_limit:confirm", "admin:basic_limit:cancel"
        ),
    )


@router.callback_query(F.data == "admin:basic_limit:confirm")
async def admin_basic_limit_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_main_admin_callback(callback):
        return
    data = await state.get_data()
    new_value = data.get("basic_limit_new")
    if not new_value:
        await callback.answer(t("admin_settings.basic_limit_invalid"), show_alert=True)
        return
    async with AsyncSessionLocal() as session:
        await set_basic_monthly_seconds(session, int(new_value), callback.from_user.id)
    settings.basic_monthly_seconds = int(new_value)
    await state.clear()
    await callback.message.answer(
        t("admin_settings.basic_limit_updated", new=new_value)
    )
    await open_admin_panel(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "admin:basic_limit:cancel")
async def admin_basic_limit_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_main_admin_callback(callback):
        return
    await state.clear()
    value = await _current_basic_limit()
    await callback.message.answer(
        t("admin_settings.basic_limit_body", value=value),
        reply_markup=admin_basic_limit_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:full_test_charge")
async def admin_full_test_charge(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_main_admin_callback(callback):
        return
    await state.set_state(AdminStates.menu)
    value = await _current_full_test_charge()
    await callback.message.edit_text(
        t("admin_settings.full_test_charge_body", value=value),
        reply_markup=admin_full_test_charge_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:full_test_charge:edit")
async def admin_full_test_charge_edit(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_main_admin_callback(callback):
        return
    await state.set_state(AdminStates.full_test_charge_edit)
    await callback.message.edit_text(t("admin_settings.full_test_charge_prompt"))
    await callback.answer()


@router.message(AdminStates.full_test_charge_edit)
async def admin_full_test_charge_value(message: Message, state: FSMContext) -> None:
    if not await ensure_main_admin_message(message):
        return
    new_value = parse_int(message.text or "")
    if not new_value or not (MIN_FULL_TEST_CHARGE <= new_value <= MAX_FULL_TEST_CHARGE):
        await message.answer(t("admin_settings.full_test_charge_invalid"))
        return
    old_value = await _current_full_test_charge()
    await state.update_data(full_test_charge_new=new_value, full_test_charge_old=old_value)
    await message.answer(
        t("admin_settings.full_test_charge_confirm", old=old_value, new=new_value),
        reply_markup=admin_confirm_kb(
            "admin:full_test_charge:confirm",
            "admin:full_test_charge:cancel",
        ),
    )


@router.callback_query(F.data == "admin:full_test_charge:confirm")
async def admin_full_test_charge_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_main_admin_callback(callback):
        return
    data = await state.get_data()
    new_value = data.get("full_test_charge_new")
    if not new_value:
        await callback.answer(t("admin_settings.full_test_charge_invalid"), show_alert=True)
        return
    async with AsyncSessionLocal() as session:
        await set_full_test_charge_seconds(session, int(new_value), callback.from_user.id)
    settings.full_test_charge_seconds = int(new_value)
    await state.clear()
    await callback.message.answer(
        t("admin_settings.full_test_charge_updated", new=new_value)
    )
    await open_admin_panel(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "admin:full_test_charge:cancel")
async def admin_full_test_charge_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_main_admin_callback(callback):
        return
    await state.clear()
    value = await _current_full_test_charge()
    await callback.message.answer(
        t("admin_settings.full_test_charge_body", value=value),
        reply_markup=admin_full_test_charge_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "admin:test_limits")
async def admin_test_limits(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_main_admin_callback(callback):
        return
    await state.set_state(AdminStates.menu)
    values = await _current_test_limits()
    await callback.message.edit_text(
        t(
            "admin_settings.test_limits_body",
            quick_count=values["quick_count"],
            quick_time=values["quick_time"],
            full_count=values["full_count"],
            full_time=values["full_time"],
        ),
        reply_markup=admin_test_limits_kb(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:test_limits:edit:"))
async def admin_test_limits_edit(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_main_admin_callback(callback):
        return
    key = _parse_test_limit_key(callback.data.rsplit(":", 1)[-1])
    if not key:
        await callback.answer()
        return
    await state.set_state(AdminStates.test_limits_edit)
    await state.update_data(test_limit_key=key)
    await callback.message.edit_text(
        t("admin_settings.test_limits_prompt", label=_test_limit_label(key)),
        reply_markup=admin_test_limits_kb(),
    )
    await callback.answer()


@router.message(AdminStates.test_limits_edit)
async def admin_test_limits_value(message: Message, state: FSMContext) -> None:
    if not await ensure_main_admin_message(message):
        return
    data = await state.get_data()
    key = _parse_test_limit_key(data.get("test_limit_key"))
    if not key:
        await state.clear()
        await message.answer(_test_limit_invalid_message("quick_count"))
        return
    new_value = parse_int(message.text or "")
    if not _is_test_limit_valid(key, new_value):
        await message.answer(_test_limit_invalid_message(key))
        return
    values = await _current_test_limits()
    old_value = values[key]
    await state.update_data(test_limit_new=new_value, test_limit_old=old_value)
    await message.answer(
        t(
            "admin_settings.test_limits_confirm",
            label=_test_limit_label(key),
            old=old_value,
            new=new_value,
        ),
        reply_markup=admin_confirm_kb(
            "admin:test_limits:confirm",
            "admin:test_limits:cancel",
        ),
    )


@router.callback_query(F.data == "admin:test_limits:confirm")
async def admin_test_limits_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_main_admin_callback(callback):
        return
    data = await state.get_data()
    key = _parse_test_limit_key(data.get("test_limit_key"))
    new_value = data.get("test_limit_new")
    if not key or not _is_test_limit_valid(key, int(new_value) if new_value else None):
        await callback.answer(_test_limit_invalid_message(key or "quick_count"), show_alert=True)
        return
    await _apply_test_limit(
        key,
        value=int(new_value),
        admin_id=callback.from_user.id,
    )
    await state.clear()
    await callback.message.answer(
        t(
            "admin_settings.test_limits_updated",
            label=_test_limit_label(key),
            new=int(new_value),
        )
    )
    await open_admin_panel(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "admin:test_limits:cancel")
async def admin_test_limits_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_main_admin_callback(callback):
        return
    await state.clear()
    values = await _current_test_limits()
    await callback.message.answer(
        t(
            "admin_settings.test_limits_body",
            quick_count=values["quick_count"],
            quick_time=values["quick_time"],
            full_count=values["full_count"],
            full_time=values["full_time"],
        ),
        reply_markup=admin_test_limits_kb(),
    )
    await callback.answer()
