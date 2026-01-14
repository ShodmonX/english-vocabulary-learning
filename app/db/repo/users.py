from datetime import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


def default_reminder_time() -> time:
    return time(20, 0)


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def get_or_create_user(session: AsyncSession, telegram_id: int) -> User:
    user = await get_user_by_telegram_id(session, telegram_id)
    if user:
        return user
    return await create_user(session, telegram_id)


async def create_user(session: AsyncSession, telegram_id: int) -> User:
    user = User(
        telegram_id=telegram_id,
        daily_goal=10,
        reminder_time=default_reminder_time(),
        timezone="Asia/Tashkent",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def update_daily_goal(session: AsyncSession, user_id: int, daily_goal: int) -> None:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    user.daily_goal = daily_goal
    await session.commit()


async def update_reminder_time(session: AsyncSession, user_id: int, reminder_time: time) -> None:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    user.reminder_time = reminder_time
    await session.commit()


async def update_reminder_enabled(session: AsyncSession, user_id: int, enabled: bool) -> None:
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    user.reminder_enabled = enabled
    await session.commit()
