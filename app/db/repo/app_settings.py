from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AppSetting

ADMIN_CONTACT_KEY = "admin_contact_username"


async def get_setting(session: AsyncSession, key: str) -> str | None:
    result = await session.execute(
        select(AppSetting).where(AppSetting.key == key)
    )
    setting = result.scalar_one_or_none()
    return setting.value if setting else None


async def set_setting(session: AsyncSession, key: str, value: str | None) -> None:
    result = await session.execute(
        select(AppSetting).where(AppSetting.key == key).with_for_update()
    )
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = value
    else:
        session.add(AppSetting(key=key, value=value))
    await session.commit()


async def get_admin_contact_username(session: AsyncSession) -> str | None:
    return await get_setting(session, ADMIN_CONTACT_KEY)


async def set_admin_contact_username(session: AsyncSession, value: str | None) -> None:
    await set_setting(session, ADMIN_CONTACT_KEY, value)
