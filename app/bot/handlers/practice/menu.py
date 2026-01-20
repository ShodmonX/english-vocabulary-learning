from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.main import main_menu_kb
from app.bot.keyboards.practice import practice_due_empty_kb, practice_menu_kb
from app.config import settings
from app.bot.handlers.practice.common import (
    build_due_items,
    build_new_items,
    edit_or_send,
    ensure_session,
    init_stats,
    update_current_review,
)
from app.bot.handlers.practice.states import PracticeStates
from app.bot.handlers.practice.summary import show_summary
from app.db.session import AsyncSessionLocal
from app.db.repo.users import get_or_create_user
from app.services.feature_flags import is_feature_enabled
from app.services.i18n import b, t

router = Router()


async def _start_mode(message: Message, state: FSMContext, mode: str, user_id: int) -> None:
    async with AsyncSessionLocal() as session:
        if not await is_feature_enabled(session, "practice"):
            await message.answer(t("practice.disabled"))
            await state.clear()
            return
    _, limit = await ensure_session(user_id)
    items = await build_due_items(user_id, limit)
    if not items:
        await state.set_state(PracticeStates.due_confirm)
        await state.update_data(pending_mode=mode)
        await edit_or_send(
            message,
            state,
            t("practice.due_done"),
            reply_markup=practice_due_empty_kb(),
        )
        return

    await state.update_data(
        word_ids=[word.id for word in items],
        items=items,
        idx=0,
        mode=mode,
        stats=init_stats(),
    )
    await update_current_review(user_id, items[0].id)
    start_line = t("practice.start_due", count=len(items))
    if mode == "quick":
        await state.set_state(PracticeStates.quick_word)
        await edit_or_send(
            message,
            state,
            f"{start_line}\n\n{_quick_word_text(1, len(items), items[0].word)}",
            reply_markup=_quick_step_kb(),
        )
    else:
        await state.set_state(PracticeStates.recall_await_answer)
        await edit_or_send(
            message,
            state,
            f"{start_line}\n\n{_recall_prompt_text(items[0].word)}",
            reply_markup=_recall_prompt_kb(),
        )


def _quick_word_text(idx: int, total: int, word: str) -> str:
    return t("practice.quick_word", index=idx, total=total, word=word)


def _recall_prompt_text(word: str) -> str:
    return t("practice.recall_prompt", word=word)


def _quick_step_kb():
    from app.bot.keyboards.practice import practice_quick_step_kb

    return practice_quick_step_kb()


def _recall_prompt_kb():
    from app.bot.keyboards.practice import practice_recall_prompt_kb

    return practice_recall_prompt_kb()


@router.callback_query(F.data == "menu:training")
async def practice_entry(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_reply_markup(reply_markup=None)
    async with AsyncSessionLocal() as session:
        if not await is_feature_enabled(session, "practice"):
            await callback.message.answer(t("practice.disabled"))
            await callback.answer()
            return
    await state.set_state(PracticeStates.menu)
    await callback.message.answer(
        t("practice.menu_prompt"), reply_markup=practice_menu_kb()
    )
    await callback.answer()


@router.message(F.text == b("menu.practice"))
async def practice_entry_text(message: Message, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        if not await is_feature_enabled(session, "practice"):
            await message.answer(t("practice.disabled"))
            return
    await state.set_state(PracticeStates.menu)
    await message.answer(t("practice.menu_prompt"), reply_markup=practice_menu_kb())


@router.callback_query(F.data.startswith("practice:mode:"))
async def practice_mode(callback: CallbackQuery, state: FSMContext) -> None:
    mode = callback.data.split(":")[-1]
    if mode not in {"quick", "recall"}:
        await callback.answer()
        return
    await callback.message.edit_reply_markup(reply_markup=None)
    await _start_mode(callback.message, state, mode, callback.from_user.id)
    await callback.answer()


@router.callback_query(PracticeStates.due_confirm, F.data == "practice:due:new")
async def practice_due_new(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    mode = data.get("pending_mode", "quick")
    _, limit = await ensure_session(callback.from_user.id)
    items = await build_new_items(callback.from_user.id, limit)
    if not items:
        await callback.message.edit_text(t("practice.no_new"))
        await state.clear()
        await callback.answer()
        return
    await state.update_data(
        word_ids=[word.id for word in items],
        items=items,
        idx=0,
        mode=mode,
        stats=init_stats(),
    )
    await update_current_review(callback.from_user.id, items[0].id)
    start_line = t("practice.start_new", count=len(items))
    if mode == "quick":
        await state.set_state(PracticeStates.quick_word)
        await edit_or_send(
            callback.message,
            state,
            f"{start_line}\n\n{_quick_word_text(1, len(items), items[0].word)}",
            reply_markup=_quick_step_kb(),
        )
    else:
        await state.set_state(PracticeStates.recall_await_answer)
        await edit_or_send(
            callback.message,
            state,
            f"{start_line}\n\n{_recall_prompt_text(items[0].word)}",
            reply_markup=_recall_prompt_kb(),
        )
    await callback.answer()


@router.callback_query(PracticeStates.due_confirm, F.data == "practice:due:exit")
async def practice_due_exit(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(t("practice.back_to_menu"), reply_markup=None)
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


@router.callback_query(F.data == "practice:menu")
async def practice_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(PracticeStates.menu)
    await callback.message.edit_text(
        t("practice.menu_prompt"), reply_markup=practice_menu_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "practice:exit")
async def practice_exit(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(t("practice.back_to_menu"), reply_markup=None)
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


@router.callback_query(F.data == "practice:stop")
async def practice_stop(callback: CallbackQuery, state: FSMContext) -> None:
    await show_summary(callback.message, state)
    await callback.answer()
