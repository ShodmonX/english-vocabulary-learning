from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TrainingSession


async def get_session(session: AsyncSession, user_id: int) -> TrainingSession | None:
    result = await session.execute(
        select(TrainingSession).where(TrainingSession.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_session(session: AsyncSession, user_id: int) -> bool:
    stmt = (
        insert(TrainingSession)
        .values(user_id=user_id)
        .on_conflict_do_nothing(index_elements=[TrainingSession.user_id])
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount == 1


async def update_session_review(
    session: AsyncSession, user_id: int, review_id: int | None
) -> None:
    db_session = await get_session(session, user_id)
    if not db_session:
        return
    db_session.current_review_id = review_id
    await session.commit()


async def delete_session(session: AsyncSession, user_id: int) -> None:
    db_session = await get_session(session, user_id)
    if not db_session:
        return
    await session.delete(db_session)
    await session.commit()
