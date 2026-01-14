from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TranslationCache


async def get_cached_translation(
    session: AsyncSession, source_text_norm: str, source_lang: str, target_lang: str
) -> str | None:
    result = await session.execute(
        select(TranslationCache.translated_text).where(
            TranslationCache.source_text_norm == source_text_norm,
            TranslationCache.source_lang == source_lang,
            TranslationCache.target_lang == target_lang,
        )
    )
    return result.scalar_one_or_none()


async def save_translation(
    session: AsyncSession,
    source_text: str,
    source_text_norm: str,
    source_lang: str,
    target_lang: str,
    translated_text: str,
) -> None:
    stmt = (
        insert(TranslationCache)
        .values(
            source_text=source_text,
            source_text_norm=source_text_norm,
            source_lang=source_lang,
            target_lang=target_lang,
            translated_text=translated_text,
        )
        .on_conflict_do_nothing(
            index_elements=[
                TranslationCache.source_text_norm,
                TranslationCache.source_lang,
                TranslationCache.target_lang,
            ]
        )
    )
    await session.execute(stmt)
    await session.commit()
