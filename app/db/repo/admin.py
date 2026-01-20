from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AdminAuditLog, CreditBalance, CreditLedger, FeatureFlag, PronunciationLog, QuizSession, ReviewLog, User, Word
from app.db.repo.app_settings import get_basic_monthly_seconds
from app.config import settings
from app.services.srs import initial_ease_factor, initial_interval_days


async def log_admin_action(
    session: AsyncSession,
    admin_user_id: int,
    action: str,
    target_type: str,
    target_id: str | None = None,
) -> None:
    session.add(
        AdminAuditLog(
            admin_user_id=admin_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
        )
    )
    await session.commit()


async def log_quiz_session(session: AsyncSession, user_id: int) -> int:
    quiz = QuizSession(user_id=user_id)
    session.add(quiz)
    await session.commit()
    await session.refresh(quiz)
    return quiz.id


async def finish_quiz_session(
    session: AsyncSession,
    session_id: int,
    total_questions: int,
    correct: int,
    wrong: int,
    accuracy: int,
) -> None:
    await session.execute(
        update(QuizSession)
        .where(QuizSession.id == session_id)
        .values(
            total_questions=total_questions,
            correct=correct,
            wrong=wrong,
            accuracy=accuracy,
            completed_at=datetime.utcnow(),
        )
    )
    await session.commit()


async def get_admin_stats(session: AsyncSession) -> dict[str, int]:
    total_users = int(
        (await session.execute(select(func.count(User.id)))).scalar_one()
    )
    total_words = int(
        (await session.execute(select(func.count(Word.id)))).scalar_one()
    )
    due_words = int(
        (
            await session.execute(
                select(func.count(Word.id)).where(Word.srs_due_at <= datetime.utcnow())
            )
        ).scalar_one()
    )
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    quiz_sessions = int(
        (
            await session.execute(
                select(func.count(QuizSession.id)).where(
                    QuizSession.created_at >= start,
                    QuizSession.created_at < end,
                )
            )
        ).scalar_one()
    )
    pronunciation_tests = int(
        (
            await session.execute(
                select(func.count(PronunciationLog.id)).where(
                    PronunciationLog.created_at >= start,
                    PronunciationLog.created_at < end,
                )
            )
        ).scalar_one()
    )
    activity_start = datetime.utcnow() - timedelta(hours=24)
    activity_count = int(
        (
            await session.execute(
                select(func.count(ReviewLog.id)).where(ReviewLog.created_at >= activity_start)
            )
        ).scalar_one()
    )
    activity_count += int(
        (
            await session.execute(
                select(func.count(QuizSession.id)).where(
                    QuizSession.created_at >= activity_start
                )
            )
        ).scalar_one()
    )
    activity_count += int(
        (
            await session.execute(
                select(func.count(PronunciationLog.id)).where(
                    PronunciationLog.created_at >= activity_start
                )
            )
        ).scalar_one()
    )
    return {
        "total_users": total_users,
        "total_words": total_words,
        "due_words": due_words,
        "quiz_sessions_today": quiz_sessions,
        "pronunciation_today": pronunciation_tests,
        "activity_24h": activity_count,
    }


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def get_user_summary(session: AsyncSession, telegram_id: int) -> dict[str, object] | None:
    user = await get_user_by_telegram_id(session, telegram_id)
    if not user:
        return None
    words_count = int(
        (
            await session.execute(
                select(func.count(Word.id)).where(Word.user_id == user.id)
            )
        ).scalar_one()
    )
    due_count = int(
        (
            await session.execute(
                select(func.count(Word.id)).where(
                    Word.user_id == user.id,
                    Word.srs_due_at <= datetime.utcnow(),
                )
            )
        ).scalar_one()
    )
    last_activity = await _get_user_last_activity(session, user.id)
    balance = await session.get(CreditBalance, user.id)
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    used_basic = (
        await session.execute(
            select(func.coalesce(func.sum(CreditLedger.basic_delta_seconds), 0)).where(
                CreditLedger.user_id == user.id,
                CreditLedger.event_type == "charge",
                CreditLedger.created_at >= month_start,
            )
        )
    ).scalar_one()
    used_basic_seconds = int(-(used_basic or 0))
    basic_limit = await get_basic_monthly_seconds(session)
    if not basic_limit or basic_limit <= 0:
        basic_limit = settings.basic_monthly_seconds
    effective_basic_remaining = 0
    if balance:
        allowed_remaining = max(0, basic_limit - used_basic_seconds)
        effective_basic_remaining = min(balance.basic_remaining_seconds, allowed_remaining)
    return {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "username": user.username,
        "is_blocked": user.is_blocked,
        "words_count": words_count,
        "due_count": due_count,
        "last_activity": last_activity,
        "basic_remaining_seconds": effective_basic_remaining,
        "topup_remaining_seconds": balance.topup_remaining_seconds if balance else 0,
        "next_basic_refill_at": balance.next_basic_refill_at if balance else None,
        "basic_monthly_seconds": basic_limit,
        "basic_used_seconds": used_basic_seconds,
    }


async def _get_user_last_activity(session: AsyncSession, user_id: int) -> datetime | None:
    last_review = (
        await session.execute(
            select(func.max(ReviewLog.created_at)).where(ReviewLog.user_id == user_id)
        )
    ).scalar_one()
    last_quiz = (
        await session.execute(
            select(func.max(QuizSession.created_at)).where(QuizSession.user_id == user_id)
        )
    ).scalar_one()
    last_pron = (
        await session.execute(
            select(func.max(PronunciationLog.created_at)).where(
                PronunciationLog.user_id == user_id
            )
        )
    ).scalar_one()
    last_word = (
        await session.execute(
            select(func.max(Word.created_at)).where(Word.user_id == user_id)
        )
    ).scalar_one()
    candidates = [dt for dt in [last_review, last_quiz, last_pron, last_word] if dt]
    return max(candidates) if candidates else None


async def set_user_blocked(session: AsyncSession, user_id: int, blocked: bool) -> None:
    await session.execute(
        update(User).where(User.id == user_id).values(is_blocked=blocked)
    )
    await session.commit()


async def srs_health_overview(session: AsyncSession) -> dict[str, object]:
    due_count = int(
        (
            await session.execute(
                select(func.count(Word.id)).where(Word.srs_due_at <= datetime.utcnow())
            )
        ).scalar_one()
    )
    learned_count = int(
        (
            await session.execute(
                select(func.count(Word.id)).where(Word.srs_repetitions > 0)
            )
        ).scalar_one()
    )
    total_words = int((await session.execute(select(func.count(Word.id)))).scalar_one())
    ratio = (due_count / total_words * 100) if total_words else 0
    top_again = await _top_again_words(session)
    return {
        "due_count": due_count,
        "learned_count": learned_count,
        "due_ratio": ratio,
        "top_again": top_again,
    }


async def _top_again_words(session: AsyncSession) -> list[tuple[str, int]]:
    result = await session.execute(
        select(Word.word, func.count(ReviewLog.id).label("cnt"))
        .join(Word, Word.id == ReviewLog.word_id)
        .where(ReviewLog.q == 0)
        .group_by(Word.word)
        .order_by(func.count(ReviewLog.id).desc())
        .limit(10)
    )
    return [(row[0], int(row[1])) for row in result.all()]


async def reset_user_srs(session: AsyncSession, user_id: int, full_reset: bool) -> None:
    values = {
        "srs_repetitions": 0,
        "srs_interval_days": initial_interval_days(),
        "srs_due_at": datetime.utcnow(),
    }
    if full_reset:
        values.update(
            {
                "srs_ease_factor": initial_ease_factor(),
                "srs_last_review_at": None,
                "srs_lapses": 0,
            }
        )
    await session.execute(update(Word).where(Word.user_id == user_id).values(**values))
    await session.commit()


async def get_feature_flag(
    session: AsyncSession, name: str, default: bool = True
) -> bool:
    result = await session.execute(select(FeatureFlag).where(FeatureFlag.name == name))
    flag = result.scalar_one_or_none()
    if not flag:
        session.add(FeatureFlag(name=name, enabled=default))
        await session.commit()
        return default
    return flag.enabled


async def set_feature_flag(session: AsyncSession, name: str, enabled: bool) -> None:
    result = await session.execute(select(FeatureFlag).where(FeatureFlag.name == name))
    flag = result.scalar_one_or_none()
    if not flag:
        session.add(FeatureFlag(name=name, enabled=enabled))
    else:
        flag.enabled = enabled
    await session.commit()
