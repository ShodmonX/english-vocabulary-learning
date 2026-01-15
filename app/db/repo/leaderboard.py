import time
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, UserPublicProfile, Word

_CACHE: dict[str, tuple[float, Any]] = {}
_CACHE_TTL_SECONDS = 60


def _cache_get(key: str):
    cached = _CACHE.get(key)
    if not cached:
        return None
    ts, value = cached
    if time.monotonic() - ts > _CACHE_TTL_SECONDS:
        _CACHE.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: Any) -> None:
    _CACHE[key] = (time.monotonic(), value)


def _profile_label(user_id: int, username: str | None, public_name: str | None, show_username: bool) -> str:
    if public_name:
        return public_name
    if show_username and username:
        return f"@{username}"
    return f"User #{str(user_id)[-4:]}"


async def get_top_current_streak(
    session: AsyncSession, page: int, page_size: int, include_all: bool = False
) -> list[dict[str, Any]]:
    key = f"streak:current:{page}:{page_size}:{include_all}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    stmt = (
        select(
            User.id,
            User.username,
            User.current_streak,
            UserPublicProfile.public_name,
            UserPublicProfile.show_username,
        )
        .join(UserPublicProfile, UserPublicProfile.user_id == User.id, isouter=True)
        .where(User.current_streak > 0)
    )
    if not include_all:
        stmt = stmt.where(UserPublicProfile.leaderboard_opt_in.is_(True))
    stmt = (
        stmt.order_by(User.current_streak.desc(), User.id.desc())
        .limit(page_size)
        .offset(page * page_size)
    )
    result = await session.execute(stmt)
    rows = result.all()
    data = [
        {
            "label": _profile_label(row.id, row.username, row.public_name, bool(row.show_username)),
            "value": row.current_streak,
        }
        for row in rows
    ]
    _cache_set(key, data)
    return data


async def get_top_longest_streak(
    session: AsyncSession, page: int, page_size: int, include_all: bool = False
) -> list[dict[str, Any]]:
    key = f"streak:longest:{page}:{page_size}:{include_all}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    stmt = (
        select(
            User.id,
            User.username,
            User.longest_streak,
            UserPublicProfile.public_name,
            UserPublicProfile.show_username,
        )
        .join(UserPublicProfile, UserPublicProfile.user_id == User.id, isouter=True)
        .where(User.longest_streak > 0)
    )
    if not include_all:
        stmt = stmt.where(UserPublicProfile.leaderboard_opt_in.is_(True))
    stmt = (
        stmt.order_by(User.longest_streak.desc(), User.id.desc())
        .limit(page_size)
        .offset(page * page_size)
    )
    result = await session.execute(stmt)
    rows = result.all()
    data = [
        {
            "label": _profile_label(row.id, row.username, row.public_name, bool(row.show_username)),
            "value": row.longest_streak,
        }
        for row in rows
    ]
    _cache_set(key, data)
    return data


async def get_top_word_count(
    session: AsyncSession, page: int, page_size: int, include_all: bool = False
) -> list[dict[str, Any]]:
    key = f"words:count:{page}:{page_size}:{include_all}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    stmt = (
        select(
            User.id,
            User.username,
            User.word_count,
            UserPublicProfile.public_name,
            UserPublicProfile.show_username,
        )
        .join(UserPublicProfile, UserPublicProfile.user_id == User.id, isouter=True)
        .where(User.word_count > 0)
    )
    if not include_all:
        stmt = stmt.where(UserPublicProfile.leaderboard_opt_in.is_(True))
    stmt = (
        stmt.order_by(User.word_count.desc(), User.id.desc())
        .limit(page_size)
        .offset(page * page_size)
    )
    result = await session.execute(stmt)
    rows = result.all()
    data = [
        {
            "label": _profile_label(row.id, row.username, row.public_name, bool(row.show_username)),
            "value": row.word_count,
        }
        for row in rows
    ]
    _cache_set(key, data)
    return data


async def get_my_word_count(session: AsyncSession, user_id: int) -> int:
    result = await session.execute(select(User.word_count).where(User.id == user_id))
    return int(result.scalar_one_or_none() or 0)


async def get_my_rank_current_streak(session: AsyncSession, user_id: int) -> int | None:
    stmt = select(func.count(User.id)).where(
        User.current_streak > 0,
        User.current_streak
        > select(User.current_streak).where(User.id == user_id).scalar_subquery(),
    )
    result = await session.execute(stmt)
    higher = int(result.scalar_one_or_none() or 0)
    return higher + 1
