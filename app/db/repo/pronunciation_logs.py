from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PronunciationLog


async def log_pronunciation(
    session: AsyncSession,
    user_id: int,
    verdict: str | None = None,
    reference_word: str | None = None,
    mode: str | None = None,
) -> None:
    session.add(
        PronunciationLog(
            user_id=user_id,
            verdict=verdict,
            reference_word=reference_word,
            mode=mode,
        )
    )
    await session.commit()


async def get_today_pronunciation_count(session: AsyncSession, user_id: int) -> int:
    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    result = await session.execute(
        select(func.count(PronunciationLog.id)).where(
            PronunciationLog.user_id == user_id,
            PronunciationLog.created_at >= start,
            PronunciationLog.created_at < end,
        )
    )
    return int(result.scalar_one())
