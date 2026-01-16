from app.db.repo.admin import get_feature_flag, set_feature_flag


FEATURE_DEFAULTS: dict[str, bool] = {
    "quiz": True,
    "pronunciation": True,
    "practice": True,
    "translation": True,
    "maintenance": False,
}


async def is_feature_enabled(session, name: str) -> bool:
    default = FEATURE_DEFAULTS.get(name, True)
    return await get_feature_flag(session, name, default=default)


async def toggle_feature(session, name: str) -> bool:
    current = await is_feature_enabled(session, name)
    await set_feature_flag(session, name, not current)
    return not current
