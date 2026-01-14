from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Review, Word
from app.services.srs import initial_ease_factor, initial_interval_days


async def get_word_by_user_word(
    session: AsyncSession, user_id: int, word: str
) -> Word | None:
    result = await session.execute(
        select(Word).where(Word.user_id == user_id, Word.word == word)
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
    new_word = Word(
        user_id=user_id,
        word=word,
        translation=translation,
        example=example,
        pos=pos,
    )
    session.add(new_word)
    await session.flush()

    review = Review(
        user_id=user_id,
        word_id=new_word.id,
        stage=0,
        ease_factor=initial_ease_factor(),
        interval_days=initial_interval_days(),
        due_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    session.add(review)
    await session.commit()
    await session.refresh(new_word)
    return new_word
