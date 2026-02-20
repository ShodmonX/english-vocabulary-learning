from __future__ import annotations

import random
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import LevelTestAttempt, LevelTestAttemptItem
from app.db.repo import level_test as repo

PLACEMENT_MODE = "PLACEMENT_30"
FULL_MODE = "FULL_30"
UI_MODE_LINEAR = "LINEAR"
UI_MODE_FLAGGED = "FLAGGED"

STATUS_ACTIVE = "ACTIVE"
STATUS_FINISHED = "FINISHED"
STATUS_EXPIRED = "EXPIRED"
STATUS_CANCELLED = "CANCELLED"

PLACEMENT_QUESTION_COUNT = int(getattr(settings, "placement_question_count", 30))
PLACEMENT_MCQ_COUNT = int(getattr(settings, "placement_mcq_count", 18))
PLACEMENT_TYPING_COUNT = int(getattr(settings, "placement_typing_count", 12))
PLACEMENT_TIME_LIMIT_SECONDS = int(getattr(settings, "placement_time_limit_seconds", 900))
FULL_QUESTION_COUNT = int(getattr(settings, "full_question_count", PLACEMENT_QUESTION_COUNT))
FULL_MCQ_COUNT = int(getattr(settings, "full_mcq_count", PLACEMENT_MCQ_COUNT))
FULL_TYPING_COUNT = int(getattr(settings, "full_typing_count", PLACEMENT_TYPING_COUNT))
FULL_TIME_LIMIT_SECONDS = int(getattr(settings, "full_time_limit_seconds", PLACEMENT_TIME_LIMIT_SECONDS))

CEFR_LEVEL_SEQUENCE: tuple[str, ...] = ("A1", "A2", "B1", "B2", "C1", "C2")

_APOSTROPHE_TRANSLATION = str.maketrans(
    {
        "’": "'",
        "‘": "'",
        "`": "'",
        "´": "'",
    }
)


@dataclass(slots=True)
class AttemptSnapshot:
    attempt: LevelTestAttempt
    item: LevelTestAttemptItem | None
    total_questions: int
    flagged_indexes: list[int]
    correct_indexes: list[int]
    remaining_seconds: int


class LevelTestError(Exception):
    pass


class QuestionBankError(LevelTestError):
    pass


def utcnow() -> datetime:
    return datetime.utcnow()


def normalize_typing_answer(value: str) -> str:
    normalized = value.translate(_APOSTROPHE_TRANSLATION).strip().lower()
    return re.sub(r"\s+", " ", normalized)


def is_typing_answer_correct(answer: str, accepted_answers: Sequence[str]) -> bool:
    normalized_answer = normalize_typing_answer(answer)
    normalized_accepted = {normalize_typing_answer(item) for item in accepted_answers if item}
    return normalized_answer in normalized_accepted


def score_to_level(score_pct: float) -> str:
    if score_pct < 30:
        return "A1"
    if score_pct < 45:
        return "A2"
    if score_pct < 60:
        return "B1"
    if score_pct < 75:
        return "B2"
    if score_pct < 90:
        return "C1"
    return "C2"


def estimate_confidence(
    *,
    answered_count: int,
    total_questions: int,
    time_spent_seconds: float,
    time_limit_seconds: int,
) -> str:
    if total_questions <= 0:
        return "low"
    answered_ratio = answered_count / total_questions
    if time_limit_seconds <= 0:
        time_ratio = 1.0
    else:
        time_ratio = max(0.0, min(1.0, time_spent_seconds / time_limit_seconds))
    if answered_ratio < 0.6 or time_ratio < 0.15:
        return "low"
    if answered_ratio >= 0.9 and time_ratio >= 0.35:
        return "high"
    return "medium"


def remaining_seconds(expires_at: datetime, now: datetime | None = None) -> int:
    current = now or utcnow()
    seconds = int((expires_at - current).total_seconds())
    return max(0, seconds)


def is_attempt_expired(expires_at: datetime, now: datetime | None = None) -> bool:
    current = now or utcnow()
    return current >= expires_at


def format_mmss(seconds: int) -> str:
    minutes, sec = divmod(max(0, seconds), 60)
    return f"{minutes:02d}:{sec:02d}"


def build_question_order(
    mcq_question_ids: Sequence[int],
    typing_question_ids: Sequence[int],
    *,
    mcq_count: int = PLACEMENT_MCQ_COUNT,
    typing_count: int = PLACEMENT_TYPING_COUNT,
    rng: random.Random | None = None,
) -> list[int]:
    if len(mcq_question_ids) < mcq_count:
        raise QuestionBankError("Not enough MCQ questions for placement test.")
    if len(typing_question_ids) < typing_count:
        raise QuestionBankError("Not enough TYPING questions for placement test.")
    ordered = list(mcq_question_ids[:mcq_count]) + list(
        typing_question_ids[:typing_count]
    )
    (rng or random).shuffle(ordered)
    return ordered


def level_path_from(level_tag: str | None) -> tuple[str, ...]:
    normalized = str(level_tag or "").strip().upper()
    if normalized not in CEFR_LEVEL_SEQUENCE:
        return CEFR_LEVEL_SEQUENCE
    start_index = CEFR_LEVEL_SEQUENCE.index(normalized)
    return CEFR_LEVEL_SEQUENCE[start_index:]


def time_limit_for_mode(mode: str) -> int:
    if mode == FULL_MODE:
        return FULL_TIME_LIMIT_SECONDS
    return PLACEMENT_TIME_LIMIT_SECONDS


def next_flagged_index(
    flagged_indexes: Sequence[int],
    current_index: int,
    *,
    forward: bool,
) -> int | None:
    if not flagged_indexes:
        return None
    ordered = sorted(flagged_indexes)
    if forward:
        for index in ordered:
            if index > current_index:
                return index
        return None
    for index in reversed(ordered):
        if index < current_index:
            return index
    return None


async def _compute_result_fields(
    session: AsyncSession,
    attempt: LevelTestAttempt,
    *,
    total_questions: int,
) -> tuple[float, str, str]:
    await repo.refresh_attempt_counters(session, attempt)
    if total_questions <= 0:
        score_pct = 0.0
    else:
        score_pct = round((attempt.correct_count / total_questions) * 100, 2)
    level_estimate = score_to_level(score_pct)
    time_spent_seconds = max(0.0, (utcnow() - attempt.started_at).total_seconds())
    confidence = estimate_confidence(
        answered_count=attempt.answered_count,
        total_questions=total_questions,
        time_spent_seconds=time_spent_seconds,
        time_limit_seconds=time_limit_for_mode(attempt.mode),
    )
    return score_pct, level_estimate, confidence


async def _finalize(
    session: AsyncSession,
    attempt: LevelTestAttempt,
    *,
    status: str,
    total_questions: int,
) -> None:
    score_pct, level_estimate, confidence = await _compute_result_fields(
        session,
        attempt,
        total_questions=total_questions,
    )
    await repo.finalize_attempt(
        session,
        attempt,
        status=status,
        score_pct=score_pct,
        level_estimate=level_estimate,
        confidence=confidence,
    )


async def _load_snapshot(
    session: AsyncSession,
    *,
    user_id: int | None = None,
    attempt_id: int | None = None,
    for_update: bool = False,
    include_inactive: bool = False,
) -> AttemptSnapshot | None:
    if user_id is None and attempt_id is None:
        raise ValueError("Either user_id or attempt_id must be provided.")
    if attempt_id is not None:
        attempt = await repo.get_attempt_by_id(session, attempt_id, for_update=for_update)
    else:
        attempt = await repo.get_active_attempt(session, int(user_id), for_update=for_update)
    if not attempt:
        return None
    if not include_inactive and attempt.status != STATUS_ACTIVE:
        return None
    total_questions = await repo.get_total_item_count(session, attempt.id)
    current_index = max(1, attempt.current_index)
    if total_questions > 0 and attempt.ui_mode == UI_MODE_LINEAR:
        current_index = min(current_index, total_questions)
    if current_index != attempt.current_index:
        await repo.save_attempt_progress(session, attempt, current_index=current_index)
    item: LevelTestAttemptItem | None = None
    if total_questions > 0:
        item = await repo.get_attempt_item_by_index(
            session,
            attempt_id=attempt.id,
            index=attempt.current_index,
            for_update=for_update,
        )
        if not item and total_questions > 0:
            attempt.current_index = 1
            await repo.save_attempt_progress(session, attempt, current_index=1)
            item = await repo.get_attempt_item_by_index(
                session,
                attempt_id=attempt.id,
                index=1,
                for_update=for_update,
            )
    flagged_indexes = await repo.list_flagged_indexes(session, attempt.id)
    correct_indexes = await repo.list_correct_indexes(session, attempt.id)
    return AttemptSnapshot(
        attempt=attempt,
        item=item,
        total_questions=total_questions,
        flagged_indexes=flagged_indexes,
        correct_indexes=correct_indexes,
        remaining_seconds=remaining_seconds(attempt.expires_at),
    )


async def get_snapshot_by_attempt_id(
    session: AsyncSession,
    attempt_id: int,
) -> AttemptSnapshot | None:
    return await _load_snapshot(
        session,
        attempt_id=attempt_id,
        include_inactive=True,
    )


async def get_active_snapshot(
    session: AsyncSession,
    user_id: int,
) -> AttemptSnapshot | None:
    snapshot = await _load_snapshot(session, user_id=user_id)
    if not snapshot:
        return None
    if is_attempt_expired(snapshot.attempt.expires_at):
        await _finalize(
            session,
            snapshot.attempt,
            status=STATUS_EXPIRED,
            total_questions=snapshot.total_questions,
        )
        await session.commit()
        return await _load_snapshot(
            session,
            attempt_id=snapshot.attempt.id,
            include_inactive=True,
        )
    return snapshot


async def get_locked_active_snapshot_for_event(
    session: AsyncSession,
    user_id: int,
) -> AttemptSnapshot | None:
    snapshot = await _load_snapshot(
        session,
        user_id=user_id,
        for_update=True,
        include_inactive=False,
    )
    if not snapshot:
        return None
    if is_attempt_expired(snapshot.attempt.expires_at):
        await _finalize(
            session,
            snapshot.attempt,
            status=STATUS_EXPIRED,
            total_questions=snapshot.total_questions,
        )
        await session.commit()
        return await _load_snapshot(
            session,
            attempt_id=snapshot.attempt.id,
            include_inactive=True,
        )
    return snapshot


async def start_or_resume_placement_attempt(
    session: AsyncSession,
    *,
    user_id: int,
    chat_id: int,
    message_id: int,
) -> LevelTestAttempt:
    return await _start_or_resume_attempt(
        session,
        user_id=user_id,
        chat_id=chat_id,
        message_id=message_id,
        mode=PLACEMENT_MODE,
        mcq_count=PLACEMENT_MCQ_COUNT,
        typing_count=PLACEMENT_TYPING_COUNT,
        time_limit_seconds=PLACEMENT_TIME_LIMIT_SECONDS,
    )


async def _pick_questions_with_optional_level_bias(
    session: AsyncSession,
    *,
    question_type: str,
    limit: int,
    preferred_levels: Sequence[str] | None = None,
) -> list[int]:
    picked_ids: list[int] = []
    if preferred_levels:
        preferred_questions = await repo.pick_random_questions(
            session,
            question_type=question_type,
            limit=limit,
            level_tags=preferred_levels,
        )
        picked_ids.extend(question.id for question in preferred_questions)
    remaining = limit - len(picked_ids)
    if remaining > 0:
        extra_questions = await repo.pick_random_questions(
            session,
            question_type=question_type,
            limit=remaining,
            exclude_ids=picked_ids,
        )
        picked_ids.extend(question.id for question in extra_questions)
    return picked_ids


async def _start_or_resume_attempt(
    session: AsyncSession,
    *,
    user_id: int,
    chat_id: int,
    message_id: int,
    mode: str,
    mcq_count: int,
    typing_count: int,
    time_limit_seconds: int,
    preferred_levels: Sequence[str] | None = None,
) -> LevelTestAttempt:
    active = await repo.get_active_attempt(session, user_id, for_update=True)
    if active:
        if is_attempt_expired(active.expires_at):
            total_questions = await repo.get_total_item_count(session, active.id)
            await _finalize(
                session,
                active,
                status=STATUS_EXPIRED,
                total_questions=total_questions,
            )
            await session.commit()
        else:
            await repo.update_attempt_message(
                session,
                active,
                chat_id=chat_id,
                message_id=message_id,
            )
            await session.commit()
            return active

    mcq_question_ids = await _pick_questions_with_optional_level_bias(
        session,
        question_type="MCQ",
        limit=mcq_count,
        preferred_levels=preferred_levels,
    )
    typing_question_ids = await _pick_questions_with_optional_level_bias(
        session,
        question_type="TYPING",
        limit=typing_count,
        preferred_levels=preferred_levels,
    )
    question_ids = build_question_order(
        mcq_question_ids,
        typing_question_ids,
        mcq_count=mcq_count,
        typing_count=typing_count,
    )

    expires_at = utcnow() + timedelta(seconds=time_limit_seconds)
    try:
        attempt = await repo.create_attempt(
            session,
            user_id=user_id,
            mode=mode,
            expires_at=expires_at,
            chat_id=chat_id,
            message_id=message_id,
        )
    except IntegrityError:
        existing = await repo.get_active_attempt(session, user_id, for_update=True)
        if existing:
            await repo.update_attempt_message(
                session,
                existing,
                chat_id=chat_id,
                message_id=message_id,
            )
            await session.commit()
            return existing
        raise

    await repo.freeze_attempt_items(
        session,
        attempt_id=attempt.id,
        question_ids=question_ids,
    )
    await repo.refresh_attempt_counters(session, attempt)
    await session.commit()
    return attempt


async def start_or_resume_full_attempt(
    session: AsyncSession,
    *,
    user_id: int,
    chat_id: int,
    message_id: int,
    start_level_tag: str,
) -> LevelTestAttempt:
    return await _start_or_resume_attempt(
        session,
        user_id=user_id,
        chat_id=chat_id,
        message_id=message_id,
        mode=FULL_MODE,
        mcq_count=FULL_MCQ_COUNT,
        typing_count=FULL_TYPING_COUNT,
        time_limit_seconds=FULL_TIME_LIMIT_SECONDS,
        preferred_levels=level_path_from(start_level_tag),
    )


async def _auto_advance_after_answer(
    session: AsyncSession,
    attempt: LevelTestAttempt,
    *,
    total_questions: int,
) -> None:
    if attempt.ui_mode == UI_MODE_LINEAR:
        if attempt.current_index < total_questions:
            await repo.save_attempt_progress(
                session,
                attempt,
                current_index=attempt.current_index + 1,
            )
            return
        flagged = await repo.list_flagged_indexes(session, attempt.id)
        if flagged:
            await repo.save_attempt_progress(
                session,
                attempt,
                ui_mode=UI_MODE_FLAGGED,
                current_index=flagged[0],
            )
            return
        await _finalize(
            session,
            attempt,
            status=STATUS_FINISHED,
            total_questions=total_questions,
        )
        return

    flagged = await repo.list_flagged_indexes(session, attempt.id)
    if not flagged:
        await _finalize(
            session,
            attempt,
            status=STATUS_FINISHED,
            total_questions=total_questions,
        )
        return
    next_index = next_flagged_index(
        flagged,
        attempt.current_index,
        forward=True,
    )
    if next_index is not None:
        await repo.save_attempt_progress(
            session,
            attempt,
            ui_mode=UI_MODE_FLAGGED,
            current_index=next_index,
        )
        return
    await _finalize(
        session,
        attempt,
        status=STATUS_FINISHED,
        total_questions=total_questions,
    )


def _accepted_answers_for_item(item: LevelTestAttemptItem) -> list[str]:
    values = list(item.question.accepted_answers or [])
    if item.question.correct_answer:
        values.append(item.question.correct_answer)
    return [value for value in values if value]


async def submit_mcq_answer(
    session: AsyncSession,
    snapshot: AttemptSnapshot,
    *,
    selected_option_index: int,
) -> LevelTestAttempt:
    item = snapshot.item
    if not item or item.question.type != "MCQ":
        return snapshot.attempt
    choices = list(item.question.choices or [])
    if selected_option_index < 0 or selected_option_index >= len(choices):
        return snapshot.attempt
    selected_text = str(choices[selected_option_index])
    correct_answer = normalize_typing_answer(item.question.correct_answer or "")
    is_correct = normalize_typing_answer(selected_text) == correct_answer
    await repo.mark_item_answer(
        session,
        item,
        payload={
            "type": "MCQ",
            "selected_index": selected_option_index,
            "selected_text": selected_text,
        },
        is_correct=is_correct,
    )
    await repo.refresh_attempt_counters(session, snapshot.attempt)
    await _auto_advance_after_answer(
        session,
        snapshot.attempt,
        total_questions=snapshot.total_questions,
    )
    await session.commit()
    return snapshot.attempt


async def submit_typing_answer(
    session: AsyncSession,
    snapshot: AttemptSnapshot,
    *,
    raw_answer: str,
) -> LevelTestAttempt:
    item = snapshot.item
    if not item or item.question.type != "TYPING":
        return snapshot.attempt
    accepted_answers = _accepted_answers_for_item(item)
    is_correct = is_typing_answer_correct(raw_answer, accepted_answers)
    await repo.mark_item_answer(
        session,
        item,
        payload={
            "type": "TYPING",
            "raw_answer": raw_answer,
            "normalized_answer": normalize_typing_answer(raw_answer),
        },
        is_correct=is_correct,
    )
    await repo.refresh_attempt_counters(session, snapshot.attempt)
    await _auto_advance_after_answer(
        session,
        snapshot.attempt,
        total_questions=snapshot.total_questions,
    )
    await session.commit()
    return snapshot.attempt


async def go_back(session: AsyncSession, snapshot: AttemptSnapshot) -> LevelTestAttempt:
    attempt = snapshot.attempt
    if attempt.ui_mode == UI_MODE_LINEAR:
        new_index = max(1, attempt.current_index - 1)
        await repo.save_attempt_progress(session, attempt, current_index=new_index)
        await session.commit()
        return attempt

    flagged = await repo.list_flagged_indexes(session, attempt.id)
    if not flagged:
        await _finalize(
            session,
            attempt,
            status=STATUS_FINISHED,
            total_questions=snapshot.total_questions,
        )
        await session.commit()
        return attempt
    new_index = next_flagged_index(flagged, attempt.current_index, forward=False)
    if new_index is not None:
        await repo.save_attempt_progress(
            session,
            attempt,
            ui_mode=UI_MODE_FLAGGED,
            current_index=new_index,
        )
    else:
        first_flagged = min(flagged)
        if first_flagged != attempt.current_index:
            await repo.save_attempt_progress(
                session,
                attempt,
                ui_mode=UI_MODE_FLAGGED,
                current_index=first_flagged,
            )
    await session.commit()
    return attempt


async def go_next_or_skip(
    session: AsyncSession,
    snapshot: AttemptSnapshot,
) -> LevelTestAttempt:
    attempt = snapshot.attempt
    if attempt.ui_mode == UI_MODE_LINEAR:
        if snapshot.item and snapshot.item.answered_at is None:
            await repo.mark_item_skipped(session, snapshot.item)
            if not snapshot.item.flagged:
                snapshot.item.flagged = True
                await session.flush()
        await repo.refresh_attempt_counters(session, attempt)
        if attempt.current_index < snapshot.total_questions:
            await repo.save_attempt_progress(
                session,
                attempt,
                current_index=attempt.current_index + 1,
            )
            await session.commit()
            return attempt
        flagged = await repo.list_flagged_indexes(session, attempt.id)
        if flagged:
            await repo.save_attempt_progress(
                session,
                attempt,
                ui_mode=UI_MODE_FLAGGED,
                current_index=flagged[0],
            )
            await session.commit()
            return attempt
        await _finalize(
            session,
            attempt,
            status=STATUS_FINISHED,
            total_questions=snapshot.total_questions,
        )
        await session.commit()
        return attempt

    flagged = await repo.list_flagged_indexes(session, attempt.id)
    if not flagged:
        await _finalize(
            session,
            attempt,
            status=STATUS_FINISHED,
            total_questions=snapshot.total_questions,
        )
        await session.commit()
        return attempt
    new_index = next_flagged_index(flagged, attempt.current_index, forward=True)
    if new_index is not None:
        await repo.save_attempt_progress(
            session,
            attempt,
            ui_mode=UI_MODE_FLAGGED,
            current_index=new_index,
        )
        await session.commit()
        return attempt
    await _finalize(
        session,
        attempt,
        status=STATUS_FINISHED,
        total_questions=snapshot.total_questions,
    )
    await session.commit()
    return attempt


async def toggle_flag(
    session: AsyncSession,
    snapshot: AttemptSnapshot,
) -> LevelTestAttempt:
    attempt = snapshot.attempt
    if not snapshot.item:
        return attempt
    await repo.toggle_item_flag(session, snapshot.item)
    await repo.refresh_attempt_counters(session, attempt)
    flagged = await repo.list_flagged_indexes(session, attempt.id)
    if attempt.ui_mode == UI_MODE_FLAGGED:
        if not flagged:
            await _finalize(
                session,
                attempt,
                status=STATUS_FINISHED,
                total_questions=snapshot.total_questions,
            )
            await session.commit()
            return attempt
        if not snapshot.item.flagged:
            next_index = next_flagged_index(
                flagged,
                snapshot.item.index,
                forward=True,
            )
            if next_index is not None:
                await repo.save_attempt_progress(
                    session,
                    attempt,
                    ui_mode=UI_MODE_FLAGGED,
                    current_index=next_index,
                )
            else:
                await _finalize(
                    session,
                    attempt,
                    status=STATUS_FINISHED,
                    total_questions=snapshot.total_questions,
                )
    await session.commit()
    return attempt


async def finish_active_attempt(
    session: AsyncSession,
    *,
    user_id: int,
    status: str = STATUS_FINISHED,
) -> LevelTestAttempt | None:
    snapshot = await _load_snapshot(
        session,
        user_id=user_id,
        for_update=True,
        include_inactive=False,
    )
    if not snapshot:
        return None
    final_status = status
    if is_attempt_expired(snapshot.attempt.expires_at):
        final_status = STATUS_EXPIRED
    await _finalize(
        session,
        snapshot.attempt,
        status=final_status,
        total_questions=snapshot.total_questions,
    )
    await session.commit()
    return snapshot.attempt


async def get_latest_estimate(
    session: AsyncSession,
    *,
    user_id: int,
) -> LevelTestAttempt | None:
    return await repo.get_latest_estimated_attempt(session, user_id=user_id, mode=PLACEMENT_MODE)


async def get_latest_finished_placement_estimate(
    session: AsyncSession,
    *,
    user_id: int,
) -> LevelTestAttempt | None:
    return await repo.get_latest_finished_estimated_attempt(
        session,
        user_id=user_id,
        mode=PLACEMENT_MODE,
    )


async def get_latest_completed_attempt(
    session: AsyncSession,
    *,
    user_id: int,
) -> LevelTestAttempt | None:
    return await repo.get_latest_completed_attempt(session, user_id=user_id)
