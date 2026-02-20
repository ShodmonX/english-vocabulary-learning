from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot.handlers.level_test_states import LevelTestStates
from app.bot.keyboards.level_test import (
    level_test_about_kb,
    level_test_entry_kb,
    level_test_question_kb,
    level_test_stop_confirm_kb,
    level_test_summary_kb,
)
from app.bot.keyboards.main import main_menu_kb
from app.config import settings
from app.db.repo.users import get_or_create_user
from app.db.session import AsyncSessionLocal
from app.services import level_test as level_test_service
from app.services.i18n import t

router = Router()


def _status_label(status: str) -> str:
    if status == level_test_service.STATUS_FINISHED:
        return t("level_test.status_finished")
    if status == level_test_service.STATUS_EXPIRED:
        return t("level_test.status_expired")
    if status == level_test_service.STATUS_CANCELLED:
        return t("level_test.status_cancelled")
    return t("level_test.status_unknown")


def _score_text(score_pct: float | None) -> str:
    if score_pct is None:
        return "0"
    normalized = f"{score_pct:.2f}"
    normalized = normalized.rstrip("0").rstrip(".")
    return normalized or "0"


def _elapsed_seconds(attempt) -> int:
    if attempt.status == level_test_service.STATUS_EXPIRED:
        end_time = attempt.expires_at
    else:
        end_time = attempt.updated_at or level_test_service.utcnow()
    elapsed = int((end_time - attempt.started_at).total_seconds())
    return max(0, min(elapsed, level_test_service.time_limit_for_mode(attempt.mode)))


def _question_text(snapshot: level_test_service.AttemptSnapshot, note: str | None = None) -> str:
    item = snapshot.item
    if not item:
        return t("level_test.no_active")
    header = t(
        "level_test.header",
        total=snapshot.total_questions,
        minutes=level_test_service.time_limit_for_mode(snapshot.attempt.mode) // 60,
    )
    progress = t(
        "level_test.progress",
        index=item.index,
        total=snapshot.total_questions,
        answered=snapshot.attempt.answered_count,
        skipped=snapshot.attempt.skipped_count,
        flagged=snapshot.attempt.flagged_count,
        time_left=level_test_service.format_mmss(snapshot.remaining_seconds),
    )
    body = item.question.prompt
    if item.question.type == "MCQ":
        choices = list(item.question.choices or [])
        if choices:
            body = f"{body}\n\n" + "\n".join(
                f"{chr(65 + idx)}) {choice}" for idx, choice in enumerate(choices)
            )
    else:
        body = f"{body}\n\n{t('level_test.typing_hint')}"
    if snapshot.attempt.ui_mode == level_test_service.UI_MODE_FLAGGED:
        body = f"{body}\n\n{t('level_test.flagged_mode')}"
    if note:
        body = f"{body}\n\n{note}"
    return f"{header}\n{progress}\n\n{body}"


def _summary_text(snapshot: level_test_service.AttemptSnapshot) -> str:
    attempt = snapshot.attempt
    summary = t(
        "level_test.summary",
        status=_status_label(attempt.status),
        correct=attempt.correct_count,
        total=snapshot.total_questions,
        score_pct=_score_text(attempt.score_pct),
        level=attempt.level_estimate or "A1",
        confidence=(attempt.confidence or "low"),
        answered=attempt.answered_count,
        skipped=attempt.skipped_count,
        flagged=attempt.flagged_count,
        elapsed=level_test_service.format_mmss(_elapsed_seconds(attempt)),
    )
    if (
        attempt.status == level_test_service.STATUS_FINISHED
        and attempt.answered_count >= snapshot.total_questions
    ):
        if snapshot.correct_indexes:
            correct_list = ", ".join(str(index) for index in snapshot.correct_indexes)
        else:
            correct_list = t("common.none")
        summary += "\n" + t(
            "level_test.correct_questions_line",
            questions=correct_list,
        )
    return summary


def _question_markup(snapshot: level_test_service.AttemptSnapshot):
    item = snapshot.item
    choices = None
    if item and item.question.type == "MCQ":
        choices = [str(choice) for choice in list(item.question.choices or [])]
    return level_test_question_kb(
        ui_mode=snapshot.attempt.ui_mode,
        current_index=item.index if item else snapshot.attempt.current_index,
        is_flagged=bool(item and item.flagged),
        is_answered=bool(item and item.answered_at is not None),
        choices=choices,
    )


async def _edit_message_safe(
    message: Message,
    *,
    text: str,
    reply_markup,
) -> None:
    try:
        await message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest as exc:
        if "message is not modified" in str(exc):
            return
        raise


async def _edit_attempt_message_from_text(
    trigger_message: Message,
    *,
    snapshot: level_test_service.AttemptSnapshot,
    note: str | None = None,
) -> None:
    if snapshot.attempt.status == level_test_service.STATUS_ACTIVE:
        text = _question_text(snapshot, note=note)
        reply_markup = _question_markup(snapshot)
    else:
        text = _summary_text(snapshot)
        reply_markup = level_test_summary_kb()
    chat_id = snapshot.attempt.chat_id
    message_id = snapshot.attempt.message_id
    if chat_id and message_id:
        try:
            await trigger_message.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
            )
            return
        except TelegramBadRequest as exc:
            if "message is not modified" in str(exc):
                return
    await trigger_message.answer(text, reply_markup=reply_markup)


async def _render_snapshot_in_callback_message(
    callback_message: Message,
    snapshot: level_test_service.AttemptSnapshot,
    *,
    note: str | None = None,
) -> None:
    if snapshot.attempt.status == level_test_service.STATUS_ACTIVE:
        await _edit_message_safe(
            callback_message,
            text=_question_text(snapshot, note=note),
            reply_markup=_question_markup(snapshot),
        )
        return
    await _edit_message_safe(
        callback_message,
        text=_summary_text(snapshot),
        reply_markup=level_test_summary_kb(),
    )


async def open_level_test_menu_message(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        t("level_test.start"),
        reply_markup=level_test_entry_kb(),
    )


@router.callback_query(F.data == "lt:menu")
async def level_test_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _edit_message_safe(
        callback.message,
        text=t("level_test.start"),
        reply_markup=level_test_entry_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "lt:about")
async def level_test_about(callback: CallbackQuery) -> None:
    await _edit_message_safe(
        callback.message,
        text=t("level_test.about"),
        reply_markup=level_test_about_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "lt:menu:main")
async def level_test_main_menu(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
    await callback.message.answer(
        t("common.main_menu"),
        reply_markup=main_menu_kb(
            is_admin=callback.from_user.id in settings.admin_user_ids,
            streak=user.current_streak,
        ),
    )
    await callback.answer()


@router.callback_query(F.data == "lt:start:quick")
async def level_test_start_quick(callback: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
        try:
            attempt = await level_test_service.start_or_resume_placement_attempt(
                session,
                user_id=user.id,
                chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
            )
        except level_test_service.QuestionBankError:
            await _edit_message_safe(
                callback.message,
                text=t("level_test.not_enough_questions"),
                reply_markup=level_test_entry_kb(),
            )
            await callback.answer()
            return
        snapshot = await level_test_service.get_snapshot_by_attempt_id(session, attempt.id)
    if not snapshot:
        await callback.answer(t("level_test.no_active"), show_alert=True)
        return
    if snapshot.attempt.status == level_test_service.STATUS_ACTIVE:
        await state.set_state(LevelTestStates.in_attempt)
    else:
        await state.clear()
    await _render_snapshot_in_callback_message(callback.message, snapshot)
    await callback.answer()


@router.callback_query(F.data == "lt:start:full")
async def level_test_start_full(callback: CallbackQuery, state: FSMContext) -> None:
    note: str | None = None
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
        quick_attempt = await level_test_service.get_latest_finished_placement_estimate(
            session,
            user_id=user.id,
        )
        try:
            if not quick_attempt or not quick_attempt.level_estimate:
                note = t("level_test.full_requires_quick_redirect")
                attempt = await level_test_service.start_or_resume_placement_attempt(
                    session,
                    user_id=user.id,
                    chat_id=callback.message.chat.id,
                    message_id=callback.message.message_id,
                )
            else:
                note = t("level_test.full_start_from_level", level=quick_attempt.level_estimate)
                attempt = await level_test_service.start_or_resume_full_attempt(
                    session,
                    user_id=user.id,
                    chat_id=callback.message.chat.id,
                    message_id=callback.message.message_id,
                    start_level_tag=quick_attempt.level_estimate,
                )
        except level_test_service.QuestionBankError:
            await _edit_message_safe(
                callback.message,
                text=t("level_test.not_enough_questions"),
                reply_markup=level_test_entry_kb(),
            )
            await callback.answer()
            return
        snapshot = await level_test_service.get_snapshot_by_attempt_id(session, attempt.id)
    if not snapshot:
        await callback.answer(t("level_test.no_active"), show_alert=True)
        return
    if snapshot.attempt.status == level_test_service.STATUS_ACTIVE:
        await state.set_state(LevelTestStates.in_attempt)
    else:
        await state.clear()
    await _render_snapshot_in_callback_message(callback.message, snapshot, note=note)
    await callback.answer()


@router.callback_query(F.data == "lt:retry")
async def level_test_retry(callback: CallbackQuery, state: FSMContext) -> None:
    note: str | None = None
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
        latest_attempt = await level_test_service.get_latest_completed_attempt(
            session,
            user_id=user.id,
        )
        try:
            if latest_attempt and latest_attempt.mode == level_test_service.FULL_MODE:
                quick_attempt = await level_test_service.get_latest_finished_placement_estimate(
                    session,
                    user_id=user.id,
                )
                if quick_attempt and quick_attempt.level_estimate:
                    note = t("level_test.full_start_from_level", level=quick_attempt.level_estimate)
                    attempt = await level_test_service.start_or_resume_full_attempt(
                        session,
                        user_id=user.id,
                        chat_id=callback.message.chat.id,
                        message_id=callback.message.message_id,
                        start_level_tag=quick_attempt.level_estimate,
                    )
                else:
                    note = t("level_test.full_requires_quick_redirect")
                    attempt = await level_test_service.start_or_resume_placement_attempt(
                        session,
                        user_id=user.id,
                        chat_id=callback.message.chat.id,
                        message_id=callback.message.message_id,
                    )
            else:
                attempt = await level_test_service.start_or_resume_placement_attempt(
                    session,
                    user_id=user.id,
                    chat_id=callback.message.chat.id,
                    message_id=callback.message.message_id,
                )
        except level_test_service.QuestionBankError:
            await _edit_message_safe(
                callback.message,
                text=t("level_test.not_enough_questions"),
                reply_markup=level_test_entry_kb(),
            )
            await callback.answer()
            return
        snapshot = await level_test_service.get_snapshot_by_attempt_id(session, attempt.id)
    if not snapshot:
        await callback.answer(t("level_test.no_active"), show_alert=True)
        return
    if snapshot.attempt.status == level_test_service.STATUS_ACTIVE:
        await state.set_state(LevelTestStates.in_attempt)
    else:
        await state.clear()
    await _render_snapshot_in_callback_message(callback.message, snapshot, note=note)
    await callback.answer()


@router.callback_query(F.data == "lt:stop")
async def level_test_stop_prompt(callback: CallbackQuery) -> None:
    await _edit_message_safe(
        callback.message,
        text=t("level_test.stop_confirm"),
        reply_markup=level_test_stop_confirm_kb(),
    )
    await callback.answer()


@router.callback_query(F.data == "lt:stop:no")
async def level_test_stop_no(callback: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
        snapshot = await level_test_service.get_active_snapshot(session, user.id)
    if not snapshot:
        await state.clear()
        await callback.answer(t("level_test.no_active"), show_alert=True)
        return
    if snapshot.attempt.status != level_test_service.STATUS_ACTIVE:
        await state.clear()
    await _render_snapshot_in_callback_message(callback.message, snapshot)
    await callback.answer()


@router.callback_query(F.data == "lt:stop:yes")
async def level_test_stop_yes(callback: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
        attempt = await level_test_service.finish_active_attempt(
            session,
            user_id=user.id,
            status=level_test_service.STATUS_CANCELLED,
        )
        if not attempt:
            await state.clear()
            await callback.answer(t("level_test.no_active"), show_alert=True)
            return
        snapshot = await level_test_service.get_snapshot_by_attempt_id(session, attempt.id)
    if not snapshot:
        await state.clear()
        await callback.answer(t("level_test.no_active"), show_alert=True)
        return
    await state.clear()
    await _render_snapshot_in_callback_message(callback.message, snapshot)
    await callback.answer()


@router.callback_query(F.data == "lt:finish")
async def level_test_finish(callback: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
        attempt = await level_test_service.finish_active_attempt(
            session,
            user_id=user.id,
            status=level_test_service.STATUS_FINISHED,
        )
        if not attempt:
            await state.clear()
            await callback.answer(t("level_test.no_active"), show_alert=True)
            return
        snapshot = await level_test_service.get_snapshot_by_attempt_id(session, attempt.id)
    if not snapshot:
        await state.clear()
        await callback.answer(t("level_test.no_active"), show_alert=True)
        return
    await state.clear()
    await _render_snapshot_in_callback_message(callback.message, snapshot)
    await callback.answer()


@router.callback_query(F.data.in_(("lt:nav:back", "lt:nav:next", "lt:flag")))
async def level_test_navigation(callback: CallbackQuery, state: FSMContext) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
        snapshot = await level_test_service.get_locked_active_snapshot_for_event(session, user.id)
        if not snapshot:
            await state.clear()
            await callback.answer(t("level_test.no_active"), show_alert=True)
            return
        if snapshot.attempt.status == level_test_service.STATUS_ACTIVE:
            if callback.data == "lt:nav:back":
                await level_test_service.go_back(session, snapshot)
            elif callback.data == "lt:nav:next":
                await level_test_service.go_next_or_skip(session, snapshot)
            else:
                await level_test_service.toggle_flag(session, snapshot)
        refreshed = await level_test_service.get_snapshot_by_attempt_id(
            session, snapshot.attempt.id
        )
    if not refreshed:
        await state.clear()
        await callback.answer(t("level_test.no_active"), show_alert=True)
        return
    if refreshed.attempt.status != level_test_service.STATUS_ACTIVE:
        await state.clear()
    await _render_snapshot_in_callback_message(callback.message, refreshed)
    await callback.answer()


@router.callback_query(F.data.startswith("lt:ans:"))
async def level_test_mcq_answer(callback: CallbackQuery, state: FSMContext) -> None:
    callback_note: str | None = None
    parts = callback.data.split(":")
    if len(parts) != 4:
        await callback.answer()
        return
    try:
        expected_index = int(parts[2])
        selected_option_index = int(parts[3])
    except ValueError:
        await callback.answer()
        return

    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, callback.from_user.id, callback.from_user.username)
        snapshot = await level_test_service.get_locked_active_snapshot_for_event(session, user.id)
        if not snapshot:
            await state.clear()
            await callback.answer(t("level_test.no_active"), show_alert=True)
            return
        if snapshot.attempt.status == level_test_service.STATUS_ACTIVE:
            if not snapshot.item or snapshot.item.index != expected_index:
                callback_note = t("level_test.question_changed")
            else:
                await level_test_service.submit_mcq_answer(
                    session,
                    snapshot,
                    selected_option_index=selected_option_index,
                )
        refreshed = await level_test_service.get_snapshot_by_attempt_id(
            session, snapshot.attempt.id
        )
    if not refreshed:
        await state.clear()
        await callback.answer(t("level_test.no_active"), show_alert=True)
        return
    if refreshed.attempt.status != level_test_service.STATUS_ACTIVE:
        await state.clear()
    await _render_snapshot_in_callback_message(callback.message, refreshed, note=callback_note)
    await callback.answer()


@router.message(LevelTestStates.in_attempt, F.text)
async def level_test_typing_answer(message: Message, state: FSMContext) -> None:
    note: str | None = None
    should_delete_input = False
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
        snapshot = await level_test_service.get_locked_active_snapshot_for_event(session, user.id)
        if not snapshot:
            await state.clear()
            return
        if snapshot.attempt.status == level_test_service.STATUS_ACTIVE:
            if not snapshot.item:
                note = t("level_test.no_active")
            elif snapshot.item.question.type != "TYPING":
                note = t("level_test.mcq_only")
            else:
                await level_test_service.submit_typing_answer(
                    session,
                    snapshot,
                    raw_answer=message.text,
                )
                should_delete_input = True
        refreshed = await level_test_service.get_snapshot_by_attempt_id(
            session, snapshot.attempt.id
        )
    if not refreshed:
        await state.clear()
        return
    if refreshed.attempt.status != level_test_service.STATUS_ACTIVE:
        await state.clear()
    if should_delete_input:
        try:
            await message.delete()
        except TelegramBadRequest:
            pass
    await _edit_attempt_message_from_text(
        message,
        snapshot=refreshed,
        note=note,
    )
