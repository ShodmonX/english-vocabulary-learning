from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.handlers.admin.common import ensure_admin_callback
from app.bot.handlers.admin.states import AdminStates
from app.bot.keyboards.admin.main import admin_back_kb
from app.bot.keyboards.admin.srs import admin_srs_reset_kb
from app.db.repo.admin import log_admin_action, reset_user_srs, srs_health_overview
from app.db.session import AsyncSessionLocal
from app.services.i18n import t

router = Router()


@router.callback_query(F.data == "admin:srs")
async def admin_srs_overview(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    async with AsyncSessionLocal() as session:
        overview = await srs_health_overview(session)
    top_lines = "\n".join([f"- {w}: {c}" for w, c in overview["top_again"]]) or t("common.none")
    text = t(
        "admin_srs.overview",
        due=overview["due_count"],
        learned=overview["learned_count"],
        ratio=f"{overview['due_ratio']:.0f}",
        top_again=top_lines,
    )
    await callback.message.edit_text(text, reply_markup=admin_back_kb())
    await callback.answer()


@router.callback_query(F.data == "admin:srs:reset")
async def admin_srs_reset_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    data = await state.get_data()
    if not data.get("admin_target_user_id"):
        await callback.answer(t("admin_srs.select_user"))
        return
    await state.set_state(AdminStates.srs_confirm)
    await callback.message.answer(
        t("admin_srs.confirm_prompt"),
        reply_markup=admin_srs_reset_kb(),
    )
    await callback.answer()


@router.callback_query(AdminStates.srs_confirm, F.data == "admin:srs:confirm:full")
async def admin_srs_reset_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    data = await state.get_data()
    user_id = data.get("admin_target_user_id")
    if not user_id:
        await callback.answer(t("admin_users.user_not_selected"))
        return
    async with AsyncSessionLocal() as session:
        await reset_user_srs(session, int(user_id), full_reset=True)
        await log_admin_action(
            session,
            callback.from_user.id,
            "srs_reset_full",
            "user",
            str(user_id),
        )
    await state.clear()
    await callback.message.answer(t("admin_srs.reset_full_done"))
    await callback.answer()


@router.callback_query(AdminStates.srs_confirm, F.data == "admin:srs:confirm:reps")
async def admin_srs_reset_reps(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    data = await state.get_data()
    user_id = data.get("admin_target_user_id")
    if not user_id:
        await callback.answer(t("admin_users.user_not_selected"))
        return
    async with AsyncSessionLocal() as session:
        await reset_user_srs(session, int(user_id), full_reset=False)
        await log_admin_action(
            session,
            callback.from_user.id,
            "srs_reset_reps",
            "user",
            str(user_id),
        )
    await state.clear()
    await callback.message.answer(t("admin_srs.reset_reps_done"))
    await callback.answer()
