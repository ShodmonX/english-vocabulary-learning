from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from app.bot.handlers.admin.common import ensure_admin_callback
from app.bot.keyboards.admin.features import admin_features_kb
from app.db.repo.admin import log_admin_action
from app.db.session import AsyncSessionLocal
from app.services.feature_flags import FEATURE_DEFAULTS, is_feature_enabled, toggle_feature
from app.services.i18n import t

router = Router()


async def _load_flags(session) -> dict[str, bool]:
    return {
        name: await is_feature_enabled(session, name)
        for name in FEATURE_DEFAULTS.keys()
    }


@router.callback_query(F.data == "admin:features")
async def admin_features(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    async with AsyncSessionLocal() as session:
        flags = await _load_flags(session)
    await callback.message.edit_text(
        t("admin_features.title"), reply_markup=admin_features_kb(flags)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:features:"))
async def admin_features_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    if not await ensure_admin_callback(callback):
        return
    name = callback.data.split(":")[-1]
    if name not in FEATURE_DEFAULTS:
        await callback.answer()
        return
    async with AsyncSessionLocal() as session:
        enabled = await toggle_feature(session, name)
        await log_admin_action(
            session,
            callback.from_user.id,
            "feature_toggle",
            "system",
            name,
        )
        flags = await _load_flags(session)
    status = t("admin_features.status_on") if enabled else t("admin_features.status_off")
    await callback.message.edit_text(
        t("admin_features.updated", name=name, status=status),
        reply_markup=admin_features_kb(flags),
    )
    await callback.answer()
