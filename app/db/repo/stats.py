from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ReviewLog, Word


async def get_today_review_stats(session: AsyncSession, user_id: int) -> dict[str, int]:
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    result = await session.execute(
        select(ReviewLog.action, func.count(ReviewLog.id))
        .where(
            ReviewLog.user_id == user_id,
            ReviewLog.created_at >= start,
            ReviewLog.created_at < end,
        )
        .group_by(ReviewLog.action)
    )
    stats = {"known": 0, "forgot": 0, "skip": 0}
    for action, count in result.all():
        stats[action] = count
    return stats


async def get_today_total(session: AsyncSession, user_id: int) -> int:
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    result = await session.execute(
        select(func.count(ReviewLog.id)).where(
            ReviewLog.user_id == user_id,
            ReviewLog.created_at >= start,
            ReviewLog.created_at < end,
        )
    )
    return int(result.scalar_one())


async def get_weekly_summary(session: AsyncSession, user_id: int) -> list[dict[str, int | date]]:
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=6)
    end = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    result = await session.execute(
        select(
            func.date(ReviewLog.created_at).label("day"),
            ReviewLog.action,
            func.count(ReviewLog.id),
        )
        .where(
            ReviewLog.user_id == user_id,
            ReviewLog.created_at >= start,
            ReviewLog.created_at < end,
        )
        .group_by(func.date(ReviewLog.created_at), ReviewLog.action)
        .order_by(func.date(ReviewLog.created_at))
    )
    stats_by_day: dict[date, dict[str, int]] = {}
    for day, action, count in result.all():
        if day not in stats_by_day:
            stats_by_day[day] = {"known": 0, "forgot": 0, "skip": 0}
        stats_by_day[day][action] = int(count)

    summary: list[dict[str, int | date]] = []
    for i in range(7):
        day = (start + timedelta(days=i)).date()
        day_stats = stats_by_day.get(day, {"known": 0, "forgot": 0, "skip": 0})
        summary.append(
            {
                "day": day,
                "known": day_stats["known"],
                "forgot": day_stats["forgot"],
                "skip": day_stats["skip"],
                "total": day_stats["known"] + day_stats["forgot"] + day_stats["skip"],
            }
        )
    return summary


async def get_total_words(session: AsyncSession, user_id: int) -> int:
    result = await session.execute(
        select(func.count(Word.id)).where(Word.user_id == user_id)
    )
    return int(result.scalar_one())


async def get_due_count(session: AsyncSession, user_id: int) -> int:
    result = await session.execute(
        select(func.count(Word.id)).where(
            Word.user_id == user_id,
            Word.srs_due_at <= datetime.utcnow(),
        )
    )
    return int(result.scalar_one())
