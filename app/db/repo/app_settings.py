from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AppSetting, SettingsChangeLog

ADMIN_CONTACT_KEY = "admin_contact_username"
BASIC_MONTHLY_SECONDS_KEY = "basic_monthly_seconds"
FULL_TEST_CHARGE_SECONDS_KEY = "full_test_charge_seconds"
PLACEMENT_QUESTION_COUNT_KEY = "placement_question_count"
PLACEMENT_TIME_LIMIT_SECONDS_KEY = "placement_time_limit_seconds"
FULL_QUESTION_COUNT_KEY = "full_question_count"
FULL_TIME_LIMIT_SECONDS_KEY = "full_time_limit_seconds"
STT_PROVIDER_KEY = "stt_provider"
PRONUNCIATION_MAX_VOICE_SECONDS_KEY = "pronunciation_max_voice_seconds"


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


async def get_full_test_charge_seconds(session: AsyncSession) -> int | None:
    value = await get_setting(session, FULL_TEST_CHARGE_SECONDS_KEY)
    if value is None:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


async def set_full_test_charge_seconds(
    session: AsyncSession, value: int, admin_id: int
) -> None:
    old_value = await get_setting(session, FULL_TEST_CHARGE_SECONDS_KEY)
    await set_setting(session, FULL_TEST_CHARGE_SECONDS_KEY, str(value))
    session.add(
        SettingsChangeLog(
            admin_id=admin_id,
            setting_key=FULL_TEST_CHARGE_SECONDS_KEY,
            old_value=old_value,
            new_value=str(value),
        )
    )
    await session.commit()


async def get_placement_question_count(session: AsyncSession) -> int | None:
    value = await get_setting(session, PLACEMENT_QUESTION_COUNT_KEY)
    if value is None:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


async def set_placement_question_count(
    session: AsyncSession, value: int, admin_id: int
) -> None:
    old_value = await get_setting(session, PLACEMENT_QUESTION_COUNT_KEY)
    await set_setting(session, PLACEMENT_QUESTION_COUNT_KEY, str(value))
    session.add(
        SettingsChangeLog(
            admin_id=admin_id,
            setting_key=PLACEMENT_QUESTION_COUNT_KEY,
            old_value=old_value,
            new_value=str(value),
        )
    )
    await session.commit()


async def get_placement_time_limit_seconds(session: AsyncSession) -> int | None:
    value = await get_setting(session, PLACEMENT_TIME_LIMIT_SECONDS_KEY)
    if value is None:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


async def set_placement_time_limit_seconds(
    session: AsyncSession, value: int, admin_id: int
) -> None:
    old_value = await get_setting(session, PLACEMENT_TIME_LIMIT_SECONDS_KEY)
    await set_setting(session, PLACEMENT_TIME_LIMIT_SECONDS_KEY, str(value))
    session.add(
        SettingsChangeLog(
            admin_id=admin_id,
            setting_key=PLACEMENT_TIME_LIMIT_SECONDS_KEY,
            old_value=old_value,
            new_value=str(value),
        )
    )
    await session.commit()


async def get_full_question_count(session: AsyncSession) -> int | None:
    value = await get_setting(session, FULL_QUESTION_COUNT_KEY)
    if value is None:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


async def set_full_question_count(
    session: AsyncSession, value: int, admin_id: int
) -> None:
    old_value = await get_setting(session, FULL_QUESTION_COUNT_KEY)
    await set_setting(session, FULL_QUESTION_COUNT_KEY, str(value))
    session.add(
        SettingsChangeLog(
            admin_id=admin_id,
            setting_key=FULL_QUESTION_COUNT_KEY,
            old_value=old_value,
            new_value=str(value),
        )
    )
    await session.commit()


async def get_full_time_limit_seconds(session: AsyncSession) -> int | None:
    value = await get_setting(session, FULL_TIME_LIMIT_SECONDS_KEY)
    if value is None:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


async def set_full_time_limit_seconds(
    session: AsyncSession, value: int, admin_id: int
) -> None:
    old_value = await get_setting(session, FULL_TIME_LIMIT_SECONDS_KEY)
    await set_setting(session, FULL_TIME_LIMIT_SECONDS_KEY, str(value))
    session.add(
        SettingsChangeLog(
            admin_id=admin_id,
            setting_key=FULL_TIME_LIMIT_SECONDS_KEY,
            old_value=old_value,
            new_value=str(value),
        )
    )
    await session.commit()


async def get_stt_provider(session: AsyncSession) -> str | None:
    value = await get_setting(session, STT_PROVIDER_KEY)
    if not value:
        return None
    normalized = value.strip().lower()
    if normalized not in {"assemblyai", "azure"}:
        return None
    return normalized


async def set_stt_provider(
    session: AsyncSession,
    value: str,
    admin_id: int,
) -> None:
    normalized = value.strip().lower()
    old_value = await get_setting(session, STT_PROVIDER_KEY)
    await set_setting(session, STT_PROVIDER_KEY, normalized)
    session.add(
        SettingsChangeLog(
            admin_id=admin_id,
            setting_key=STT_PROVIDER_KEY,
            old_value=old_value,
            new_value=normalized,
        )
    )
    await session.commit()


async def get_pronunciation_max_voice_seconds(session: AsyncSession) -> int | None:
    value = await get_setting(session, PRONUNCIATION_MAX_VOICE_SECONDS_KEY)
    if value is None:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


async def set_pronunciation_max_voice_seconds(
    session: AsyncSession,
    value: int,
    admin_id: int,
) -> None:
    old_value = await get_setting(session, PRONUNCIATION_MAX_VOICE_SECONDS_KEY)
    await set_setting(session, PRONUNCIATION_MAX_VOICE_SECONDS_KEY, str(value))
    session.add(
        SettingsChangeLog(
            admin_id=admin_id,
            setting_key=PRONUNCIATION_MAX_VOICE_SECONDS_KEY,
            old_value=old_value,
            new_value=str(value),
        )
    )
    await session.commit()
