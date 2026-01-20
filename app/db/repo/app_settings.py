from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AppSetting, SettingsChangeLog

ADMIN_CONTACT_KEY = "admin_contact_username"
BASIC_MONTHLY_SECONDS_KEY = "basic_monthly_seconds"


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


async def get_basic_monthly_seconds(session: AsyncSession) -> int | None:
    value = await get_setting(session, BASIC_MONTHLY_SECONDS_KEY)
    if value is None:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


async def set_basic_monthly_seconds(
    session: AsyncSession, value: int, admin_id: int
) -> None:
    old_value = await get_setting(session, BASIC_MONTHLY_SECONDS_KEY)
    await set_setting(session, BASIC_MONTHLY_SECONDS_KEY, str(value))
    session.add(
        SettingsChangeLog(
            admin_id=admin_id,
            setting_key=BASIC_MONTHLY_SECONDS_KEY,
            old_value=old_value,
            new_value=str(value),
        )
    )
    await session.commit()
