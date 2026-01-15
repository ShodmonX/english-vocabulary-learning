from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ReviewLog, User, Word
from app.services.srs import sm2_update


async def get_due_words(session: AsyncSession, user_id: int, limit: int) -> list[Word]:
    result = await session.execute(
        select(Word)
        .where(Word.user_id == user_id, Word.srs_due_at <= datetime.utcnow())
        .order_by(Word.srs_due_at.asc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_new_words(session: AsyncSession, user_id: int, limit: int) -> list[Word]:
    result = await session.execute(
        select(Word)
        .where(Word.user_id == user_id, Word.srs_repetitions == 0)
        .order_by(Word.created_at.asc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def apply_review(session: AsyncSession, word: Word, q: int) -> None:
    ef_before = word.srs_ease_factor
    interval_before = word.srs_interval_days
    lapses_before = word.srs_lapses

    reps, interval, ef, due_at, lapses = sm2_update(
        repetitions=word.srs_repetitions,
        interval_days=word.srs_interval_days,
        ease_factor=word.srs_ease_factor,
        q=q,
    )

    word.srs_repetitions = reps
    word.srs_interval_days = interval
    word.srs_ease_factor = ef
    word.srs_due_at = due_at
    word.srs_last_review_at = datetime.utcnow()
    await _update_streak(session, word.user_id)
    if lapses:
        word.srs_lapses = lapses_before + lapses

    action = "known" if q >= 4 else "skip" if q == 3 else "forgot"
    log = ReviewLog(
        user_id=word.user_id,
        word_id=word.id,
        action=action,
        q=q,
        ef_before=ef_before,
        ef_after=ef,
        interval_before=interval_before,
        interval_after=interval,
    )
    session.add(log)
    await session.commit()


async def _update_streak(session: AsyncSession, user_id: int) -> None:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return
    try:
        now = datetime.now(ZoneInfo(user.timezone or "UTC"))
    except Exception:
        now = datetime.utcnow()
    today = now.date()
    last = user.last_review_date
    if last is None:
        user.current_streak = 1
    elif last == today:
        pass
    elif last == today - timedelta(days=1):
        user.current_streak += 1
    else:
        user.current_streak = 1
    user.last_review_date = today
    if user.current_streak > user.longest_streak:
        user.longest_streak = user.current_streak
