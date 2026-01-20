from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BotAdmin


async def get_admin(session: AsyncSession, tg_user_id: int) -> BotAdmin | None:
    result = await session.execute(
        select(BotAdmin).where(BotAdmin.tg_user_id == tg_user_id)
    )
    return result.scalar_one_or_none()


async def list_admins(session: AsyncSession) -> list[BotAdmin]:
    result = await session.execute(select(BotAdmin).order_by(BotAdmin.added_at.asc()))
    return list(result.scalars().all())


async def ensure_owner_admin(
    session: AsyncSession, tg_user_id: int, first_name: str, username: str | None
) -> BotAdmin:
    admin = await get_admin(session, tg_user_id)
    if admin:
        if not admin.is_owner:
            admin.is_owner = True
            admin.added_by = tg_user_id
        if first_name and admin.first_name != first_name:
            admin.first_name = first_name
        if username and admin.username != username:
            admin.username = username
        await session.commit()
        return admin
    admin = BotAdmin(
        tg_user_id=tg_user_id,
        first_name=first_name or str(tg_user_id),
        username=username,
        added_by=tg_user_id,
        is_owner=True,
    )
    session.add(admin)
    await session.commit()
    await session.refresh(admin)
    return admin


async def upsert_admin(
    session: AsyncSession,
    tg_user_id: int,
    first_name: str,
    username: str | None,
    added_by: int,
) -> BotAdmin:
    admin = await get_admin(session, tg_user_id)
    if admin:
        admin.first_name = first_name or admin.first_name
        admin.username = username or admin.username
        await session.commit()
        return admin
    admin = BotAdmin(
        tg_user_id=tg_user_id,
        first_name=first_name or str(tg_user_id),
        username=username,
        added_by=added_by,
        is_owner=False,
    )
    session.add(admin)
    await session.commit()
    await session.refresh(admin)
    return admin


async def remove_admin(session: AsyncSession, tg_user_id: int) -> bool:
    admin = await get_admin(session, tg_user_id)
    if not admin or admin.is_owner:
        return False
    await session.delete(admin)
    await session.commit()
    return True


async def mark_owner(session: AsyncSession, tg_user_id: int) -> None:
    await session.execute(
        update(BotAdmin)
        .where(BotAdmin.tg_user_id == tg_user_id)
        .values(is_owner=True)
    )
    await session.commit()
