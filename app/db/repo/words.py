from datetime import datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Review, ReviewLog, TrainingSession, User, Word
from app.services.srs import initial_ease_factor, initial_interval_days


async def get_word_by_user_word(
    session: AsyncSession, user_id: int, word: str
) -> Word | None:
    word_norm = word.strip().lower()
    result = await session.execute(
        select(Word).where(
            Word.user_id == user_id,
            func.lower(Word.word) == word_norm,
        )
    )
    return result.scalar_one_or_none()


async def create_word_with_review(
    session: AsyncSession,
    user_id: int,
    word: str,
    translation: str,
    example: str | None,
    pos: str | None,
) -> Word:
    word_norm = word.strip().lower()
    translation_norm = translation.strip().lower()
    new_word = Word(
        user_id=user_id,
        word=word_norm,
        translation=translation_norm,
        example=example,
        pos=pos,
        srs_repetitions=0,
        srs_interval_days=initial_interval_days(),
        srs_ease_factor=initial_ease_factor(),
        srs_due_at=datetime.utcnow(),
    )
    session.add(new_word)
    await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(word_count=User.word_count + 1)
    )
    await session.commit()
    await session.refresh(new_word)
    return new_word


async def get_words_by_user(session: AsyncSession, user_id: int) -> list[Word]:
    result = await session.execute(select(Word).where(Word.user_id == user_id))
    return list(result.scalars().all())


async def list_recent_words(
    session: AsyncSession, user_id: int, limit: int, offset: int
) -> list[Word]:
    result = await session.execute(
        select(Word)
        .where(Word.user_id == user_id)
        .order_by(Word.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def search_words(
    session: AsyncSession, user_id: int, query: str, limit: int, offset: int
) -> list[Word]:
    pattern = f"%{query}%"
    result = await session.execute(
        select(Word)
        .where(Word.user_id == user_id, Word.word.ilike(pattern))
        .order_by(Word.word.asc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def get_word(session: AsyncSession, user_id: int, word_id: int) -> Word | None:
    result = await session.execute(
        select(Word).where(Word.user_id == user_id, Word.id == word_id)
    )
    return result.scalar_one_or_none()


async def update_word_text(
    session: AsyncSession, user_id: int, word_id: int, new_word: str
) -> None:
    word = await get_word(session, user_id, word_id)
    if not word:
        return
    word.word = new_word.strip().lower()
    await session.commit()


async def update_translation(
    session: AsyncSession, user_id: int, word_id: int, new_translation: str
) -> None:
    word = await get_word(session, user_id, word_id)
    if not word:
        return
    word.translation = new_translation.strip().lower()
    await session.commit()


async def update_example(
    session: AsyncSession, user_id: int, word_id: int, new_example: str | None
) -> None:
    word = await get_word(session, user_id, word_id)
    if not word:
        return
    word.example = new_example
    await session.commit()


async def delete_word(session: AsyncSession, user_id: int, word_id: int) -> None:
    word = await get_word(session, user_id, word_id)
    if not word:
        return
    await session.execute(
        update(TrainingSession)
        .where(TrainingSession.user_id == user_id, TrainingSession.current_word_id == word_id)
        .values(current_word_id=None)
    )
    await session.execute(
        delete(ReviewLog).where(ReviewLog.word_id == word_id, ReviewLog.user_id == user_id)
    )
    await session.execute(
        delete(Review).where(Review.word_id == word_id, Review.user_id == user_id)
    )
    await session.execute(
        update(User)
        .where(User.id == user_id, User.word_count > 0)
        .values(word_count=User.word_count - 1)
    )
    await session.delete(word)
    await session.commit()


async def exists_word(
    session: AsyncSession, user_id: int, word_text: str, exclude_word_id: int | None = None
) -> bool:
    word_norm = word_text.strip().lower()
    stmt = select(func.count(Word.id)).where(
        Word.user_id == user_id,
        func.lower(Word.word) == word_norm,
    )
    if exclude_word_id is not None:
        stmt = stmt.where(Word.id != exclude_word_id)
    result = await session.execute(stmt)
    return int(result.scalar_one()) > 0


async def find_words_by_translation(
    session: AsyncSession,
    user_id: int,
    translation_text: str,
    exclude_word_id: int | None = None,
) -> list[Word]:
    stmt = select(Word).where(
        Word.user_id == user_id, Word.translation == translation_text
    )
    if exclude_word_id is not None:
        stmt = stmt.where(Word.id != exclude_word_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def count_words(session: AsyncSession, user_id: int) -> int:
    result = await session.execute(
        select(func.count(Word.id)).where(Word.user_id == user_id)
    )
    return int(result.scalar_one())


async def count_words_today(session: AsyncSession, user_id: int) -> int:
    from datetime import datetime, timedelta

    start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    result = await session.execute(
        select(func.count(Word.id)).where(
            Word.user_id == user_id,
            Word.created_at >= start,
            Word.created_at < end,
        )
    )
    return int(result.scalar_one())
