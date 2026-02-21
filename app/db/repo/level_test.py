from __future__ import annotations

from datetime import datetime
import re
from typing import Sequence

from sqlalchemy import case, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import LevelTestAttempt, LevelTestAttemptItem, LevelTestQuestion


def utcnow() -> datetime:
    return datetime.utcnow()


def _normalize_prompt(value: str | None) -> str:
    raw = (value or "").strip().lower()
    if not raw:
        return ""
    return re.sub(r"\s+", " ", raw)


async def get_active_attempt(
    session: AsyncSession,
    user_id: int,
    *,
    for_update: bool = False,
) -> LevelTestAttempt | None:
    stmt = (
        select(LevelTestAttempt)
        .where(
            LevelTestAttempt.user_id == user_id,
            LevelTestAttempt.status == "ACTIVE",
        )
        .order_by(LevelTestAttempt.id.desc())
    )
    if for_update:
        stmt = stmt.with_for_update()
    result = await session.execute(stmt)
    return result.scalars().first()


async def get_attempt_by_id(
    session: AsyncSession,
    attempt_id: int,
    *,
    for_update: bool = False,
) -> LevelTestAttempt | None:
    stmt = select(LevelTestAttempt).where(LevelTestAttempt.id == attempt_id)
    if for_update:
        stmt = stmt.with_for_update()
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def create_attempt(
    session: AsyncSession,
    *,
    user_id: int,
    mode: str,
    expires_at: datetime,
    chat_id: int | None = None,
    message_id: int | None = None,
) -> LevelTestAttempt:
    attempt = LevelTestAttempt(
        user_id=user_id,
        mode=mode,
        ui_mode="LINEAR",
        current_index=1,
        started_at=utcnow(),
        expires_at=expires_at,
        status="ACTIVE",
        chat_id=chat_id,
        message_id=message_id,
    )
    session.add(attempt)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        raise
    return attempt


async def update_attempt_message(
    session: AsyncSession,
    attempt: LevelTestAttempt,
    *,
    chat_id: int | None,
    message_id: int | None,
) -> None:
    attempt.chat_id = chat_id
    attempt.message_id = message_id
    attempt.updated_at = utcnow()
    await session.flush()


async def pick_random_questions(
    session: AsyncSession,
    *,
    question_type: str,
    limit: int,
    level_tags: Sequence[str] | None = None,
    exclude_ids: Sequence[int] | None = None,
) -> list[LevelTestQuestion]:
    if limit <= 0:
        return []
    stmt = select(LevelTestQuestion).where(
        LevelTestQuestion.is_active.is_(True),
        LevelTestQuestion.type == question_type,
    )
    if level_tags:
        normalized_levels = [str(level).strip().upper() for level in level_tags if str(level).strip()]
        if normalized_levels:
            stmt = stmt.where(LevelTestQuestion.level_tag.in_(normalized_levels))
    if exclude_ids:
        normalized_ids = [int(item) for item in exclude_ids]
        if normalized_ids:
            stmt = stmt.where(~LevelTestQuestion.id.in_(normalized_ids))
    result = await session.execute(stmt.order_by(func.random()).limit(limit))
    return list(result.scalars().all())


async def list_question_prompt_keys(session: AsyncSession) -> set[tuple[str, str]]:
    result = await session.execute(select(LevelTestQuestion.type, LevelTestQuestion.prompt))
    keys: set[tuple[str, str]] = set()
    for question_type, prompt in result.all():
        normalized_prompt = _normalize_prompt(prompt)
        if normalized_prompt:
            keys.add((str(question_type).upper(), normalized_prompt))
    return keys


async def create_question(
    session: AsyncSession,
    *,
    level_tag: str,
    difficulty: int,
    question_type: str,
    prompt: str,
    choices: list[str] | None,
    correct_answer: str | None,
    accepted_answers: list[str] | None,
    explanation: str | None,
    is_active: bool = True,
) -> LevelTestQuestion:
    question = LevelTestQuestion(
        level_tag=level_tag,
        difficulty=difficulty,
        type=question_type,
        prompt=prompt,
        choices=choices,
        correct_answer=correct_answer,
        accepted_answers=accepted_answers,
        explanation=explanation,
        is_active=is_active,
    )
    session.add(question)
    await session.flush()
    return question


async def freeze_attempt_items(
    session: AsyncSession,
    *,
    attempt_id: int,
    question_ids: list[int],
) -> list[LevelTestAttemptItem]:
    items: list[LevelTestAttemptItem] = []
    for index, question_id in enumerate(question_ids, start=1):
        item = LevelTestAttemptItem(
            attempt_id=attempt_id,
            index=index,
            question_id=question_id,
            flagged=False,
            skipped=False,
        )
        session.add(item)
        items.append(item)
    await session.flush()
    return items


async def list_attempt_items(
    session: AsyncSession,
    attempt_id: int,
) -> list[LevelTestAttemptItem]:
    result = await session.execute(
        select(LevelTestAttemptItem)
        .options(selectinload(LevelTestAttemptItem.question))
        .where(LevelTestAttemptItem.attempt_id == attempt_id)
        .order_by(LevelTestAttemptItem.index.asc())
    )
    return list(result.scalars().all())


async def get_attempt_item_by_index(
    session: AsyncSession,
    *,
    attempt_id: int,
    index: int,
    for_update: bool = False,
) -> LevelTestAttemptItem | None:
    stmt = (
        select(LevelTestAttemptItem)
        .options(selectinload(LevelTestAttemptItem.question))
        .where(
            LevelTestAttemptItem.attempt_id == attempt_id,
            LevelTestAttemptItem.index == index,
        )
    )
    if for_update:
        stmt = stmt.with_for_update()
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def refresh_attempt_counters(
    session: AsyncSession,
    attempt: LevelTestAttempt,
) -> None:
    result = await session.execute(
        select(
            func.coalesce(
                func.sum(
                    case((LevelTestAttemptItem.answered_at.is_not(None), 1), else_=0)
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    case((LevelTestAttemptItem.is_correct.is_(True), 1), else_=0)
                ),
                0,
            ),
            func.coalesce(
                func.sum(case((LevelTestAttemptItem.skipped.is_(True), 1), else_=0)),
                0,
            ),
            func.coalesce(
                func.sum(case((LevelTestAttemptItem.flagged.is_(True), 1), else_=0)),
                0,
            ),
        ).where(LevelTestAttemptItem.attempt_id == attempt.id)
    )
    answered_count, correct_count, skipped_count, flagged_count = result.one()
    attempt.answered_count = int(answered_count or 0)
    attempt.correct_count = int(correct_count or 0)
    attempt.skipped_count = int(skipped_count or 0)
    attempt.flagged_count = int(flagged_count or 0)
    attempt.updated_at = utcnow()
    await session.flush()


async def mark_item_answer(
    session: AsyncSession,
    item: LevelTestAttemptItem,
    *,
    payload: dict[str, object],
    is_correct: bool,
) -> None:
    item.answer_payload = payload
    item.is_correct = is_correct
    item.skipped = False
    item.answered_at = utcnow()
    await session.flush()


async def mark_item_skipped(session: AsyncSession, item: LevelTestAttemptItem) -> None:
    if item.answered_at is None:
        item.skipped = True
        await session.flush()


async def toggle_item_flag(session: AsyncSession, item: LevelTestAttemptItem) -> bool:
    item.flagged = not item.flagged
    await session.flush()
    return item.flagged


async def list_flagged_indexes(session: AsyncSession, attempt_id: int) -> list[int]:
    result = await session.execute(
        select(LevelTestAttemptItem.index)
        .where(
            LevelTestAttemptItem.attempt_id == attempt_id,
            LevelTestAttemptItem.flagged.is_(True),
        )
        .order_by(LevelTestAttemptItem.index.asc())
    )
    return [int(value) for value in result.scalars().all()]


async def list_correct_indexes(session: AsyncSession, attempt_id: int) -> list[int]:
    result = await session.execute(
        select(LevelTestAttemptItem.index)
        .where(
            LevelTestAttemptItem.attempt_id == attempt_id,
            LevelTestAttemptItem.is_correct.is_(True),
        )
        .order_by(LevelTestAttemptItem.index.asc())
    )
    return [int(value) for value in result.scalars().all()]


async def get_total_item_count(session: AsyncSession, attempt_id: int) -> int:
    result = await session.execute(
        select(func.count(LevelTestAttemptItem.id)).where(
            LevelTestAttemptItem.attempt_id == attempt_id
        )
    )
    return int(result.scalar_one() or 0)


async def save_attempt_progress(
    session: AsyncSession,
    attempt: LevelTestAttempt,
    *,
    ui_mode: str | None = None,
    current_index: int | None = None,
) -> None:
    if ui_mode is not None:
        attempt.ui_mode = ui_mode
    if current_index is not None:
        attempt.current_index = current_index
    attempt.updated_at = utcnow()
    await session.flush()


async def finalize_attempt(
    session: AsyncSession,
    attempt: LevelTestAttempt,
    *,
    status: str,
    score_pct: float,
    level_estimate: str,
    confidence: str,
) -> None:
    attempt.status = status
    attempt.score_pct = score_pct
    attempt.level_estimate = level_estimate
    attempt.confidence = confidence
    attempt.updated_at = utcnow()
    await session.flush()


async def get_latest_estimated_attempt(
    session: AsyncSession,
    *,
    user_id: int,
    mode: str = "PLACEMENT_30",
) -> LevelTestAttempt | None:
    result = await session.execute(
        select(LevelTestAttempt)
        .where(
            LevelTestAttempt.user_id == user_id,
            LevelTestAttempt.mode == mode,
            LevelTestAttempt.status.in_(("FINISHED", "EXPIRED", "CANCELLED")),
            LevelTestAttempt.level_estimate.is_not(None),
        )
        .order_by(LevelTestAttempt.updated_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_latest_finished_estimated_attempt(
    session: AsyncSession,
    *,
    user_id: int,
    mode: str = "PLACEMENT_30",
) -> LevelTestAttempt | None:
    result = await session.execute(
        select(LevelTestAttempt)
        .where(
            LevelTestAttempt.user_id == user_id,
            LevelTestAttempt.mode == mode,
            LevelTestAttempt.status == "FINISHED",
            LevelTestAttempt.level_estimate.is_not(None),
        )
        .order_by(LevelTestAttempt.updated_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_latest_completed_attempt(
    session: AsyncSession,
    *,
    user_id: int,
) -> LevelTestAttempt | None:
    result = await session.execute(
        select(LevelTestAttempt)
        .where(
            LevelTestAttempt.user_id == user_id,
            LevelTestAttempt.status.in_(("FINISHED", "EXPIRED", "CANCELLED")),
        )
        .order_by(LevelTestAttempt.updated_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def list_completed_full_attempts_in_period(
    session: AsyncSession,
    *,
    user_id: int,
    from_utc: datetime,
    to_utc: datetime,
) -> list[LevelTestAttempt]:
    result = await session.execute(
        select(LevelTestAttempt)
        .where(
            LevelTestAttempt.user_id == user_id,
            LevelTestAttempt.mode.like("FULL_%"),
            LevelTestAttempt.status.in_(("FINISHED", "EXPIRED", "CANCELLED")),
            LevelTestAttempt.updated_at >= from_utc,
            LevelTestAttempt.updated_at < to_utc,
        )
        .order_by(LevelTestAttempt.updated_at.asc(), LevelTestAttempt.id.asc())
    )
    return list(result.scalars().all())


async def get_latest_confirmed_estimated_attempt(
    session: AsyncSession,
    *,
    user_id: int,
    excluded_modes: tuple[str, ...] = ("PLACEMENT_30",),
) -> LevelTestAttempt | None:
    stmt = (
        select(LevelTestAttempt)
        .where(
            LevelTestAttempt.user_id == user_id,
            LevelTestAttempt.status == "FINISHED",
            LevelTestAttempt.level_estimate.is_not(None),
        )
        .order_by(LevelTestAttempt.updated_at.desc())
        .limit(1)
    )
    if excluded_modes:
        stmt = stmt.where(~LevelTestAttempt.mode.in_(excluded_modes))
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
