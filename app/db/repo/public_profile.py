from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import UserPublicProfile


async def get_or_create_profile(
    session: AsyncSession, user_id: int
) -> UserPublicProfile:
    profile = await session.get(UserPublicProfile, user_id)
    if profile:
        return profile
    profile = UserPublicProfile(
        user_id=user_id,
        leaderboard_opt_in=False,
        show_username=False,
        updated_at=datetime.utcnow(),
    )
    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    return profile


async def set_opt_in(session: AsyncSession, user_id: int, enabled: bool) -> None:
    await session.execute(
        update(UserPublicProfile)
        .where(UserPublicProfile.user_id == user_id)
        .values(leaderboard_opt_in=enabled, updated_at=datetime.utcnow())
    )
    await session.commit()


async def set_public_name(
    session: AsyncSession, user_id: int, name: str | None
) -> None:
    await session.execute(
        update(UserPublicProfile)
        .where(UserPublicProfile.user_id == user_id)
        .values(public_name=name, updated_at=datetime.utcnow())
    )
    await session.commit()


async def set_show_username(
    session: AsyncSession, user_id: int, enabled: bool
) -> None:
    await session.execute(
        update(UserPublicProfile)
        .where(UserPublicProfile.user_id == user_id)
        .values(show_username=enabled, updated_at=datetime.utcnow())
    )
    await session.commit()
