from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Review, ReviewLog, Word


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


async def get_total_words(session: AsyncSession, user_id: int) -> int:
    result = await session.execute(
        select(func.count(Word.id)).where(Word.user_id == user_id)
    )
    return int(result.scalar_one())


async def get_due_count(session: AsyncSession, user_id: int) -> int:
    result = await session.execute(
        select(func.count(Review.id)).where(
            Review.user_id == user_id,
            Review.due_at <= datetime.utcnow(),
        )
    )
    return int(result.scalar_one())
