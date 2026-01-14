from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models import Review, ReviewLog, Word


async def get_due_reviews(session: AsyncSession, user_id: int) -> list[Review]:
    result = await session.execute(
        select(Review)
        .options(joinedload(Review.word))
        .where(Review.user_id == user_id, Review.due_at <= datetime.utcnow())
        .order_by(Review.due_at.asc())
    )
    return list(result.scalars().all())


async def get_review_by_id(session: AsyncSession, review_id: int) -> Review | None:
    result = await session.execute(
        select(Review).options(joinedload(Review.word)).where(Review.id == review_id)
    )
    return result.scalar_one_or_none()


async def update_review(
    session: AsyncSession, review: Review, stage: int, due_at: datetime
) -> None:
    review.stage = stage
    review.due_at = due_at
    review.updated_at = datetime.utcnow()
    await session.commit()


async def log_review(session: AsyncSession, user_id: int, word_id: int, action: str) -> None:
    log = ReviewLog(user_id=user_id, word_id=word_id, action=action)
    session.add(log)
    await session.commit()


async def get_word_details_by_review(
    session: AsyncSession, review_id: int
) -> Word | None:
    review = await get_review_by_id(session, review_id)
    if not review:
        return None
    return review.word
