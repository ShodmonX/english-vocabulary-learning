from __future__ import annotations

from datetime import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, UserSettings


def _default_notification_time() -> time:
    return time(20, 0)


async def get_user_settings(
    session: AsyncSession, user_id: int
) -> UserSettings | None:
    result = await session.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_or_create_user_settings(
    session: AsyncSession, user: User
) -> UserSettings:
    result = await session.execute(
        select(UserSettings).where(UserSettings.user_id == user.id)
    )
    settings = result.scalar_one_or_none()
    if settings:
        return settings

    settings = UserSettings(
        user_id=user.id,
        learning_words_per_day=user.daily_goal,
        notifications_enabled=user.reminder_enabled,
        notification_time=user.reminder_time or _default_notification_time(),
    )
    session.add(settings)
    await session.commit()
    await session.refresh(settings)
    return settings


async def update_user_settings(
    session: AsyncSession, user_id: int, **fields: object
) -> UserSettings:
    result = await session.execute(
        select(UserSettings).where(UserSettings.user_id == user_id)
    )
    settings = result.scalar_one()
    for key, value in fields.items():
        setattr(settings, key, value)
    await session.commit()
    await session.refresh(settings)
    return settings


async def reset_user_settings(session: AsyncSession, user: User) -> UserSettings:
    result = await session.execute(
        select(UserSettings).where(UserSettings.user_id == user.id)
    )
    settings = result.scalar_one()
    settings.learning_words_per_day = 10
    settings.quiz_words_per_session = 10
    settings.pronunciation_enabled = True
    settings.pronunciation_mode = "both"
    settings.translation_enabled = True
    settings.translation_engine = "google"
    settings.auto_translation_suggest = True
    settings.daily_limit_enabled = True
    settings.daily_pronunciation_limit = 10
    settings.notifications_enabled = False
    settings.notification_time = _default_notification_time()
    await session.commit()
    await session.refresh(settings)
    return settings
