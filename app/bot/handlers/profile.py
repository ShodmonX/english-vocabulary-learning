from __future__ import annotations

from datetime import timezone
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.profile import profile_refresh_kb
from app.config import settings
from app.db.repo.credits import get_profile_summary
from app.db.repo.users import get_or_create_user
from app.db.session import AsyncSessionLocal

router = Router()


def _format_refill(dt) -> str:
    tz = ZoneInfo(settings.timezone)
    local_dt = dt.replace(tzinfo=timezone.utc).astimezone(tz)
    return local_dt.strftime("%Y-%m-%d %H:%M")


def _profile_text(user, summary: dict[str, object]) -> str:
    username = f"@{user.username}" if user.username else "—"
    return (
        "👤 Profil\n"
        f"ID: {user.telegram_id}\n"
        f"Username: {username}\n\n"
        f"BASIC: {summary['basic_remaining_seconds']}s\n"
        f"TOPUP: {summary['topup_remaining_seconds']}s\n"
        f"Keyingi refill: {_format_refill(summary['next_basic_refill_at'])} ({settings.timezone})\n"
        f"Oy bo‘yicha ishlatilgan: {summary['monthly_used_seconds']}s"
    )


async def _render_profile(message: Message) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(session, message.from_user.id, message.from_user.username)
        summary = await get_profile_summary(session, user.id)
    await message.answer(_profile_text(user, summary), reply_markup=profile_refresh_kb())


@router.message(F.text == "👤 Profil")
async def profile_menu(message: Message) -> None:
    await _render_profile(message)


@router.message(F.text == "/profile")
async def profile_command(message: Message) -> None:
    await _render_profile(message)


@router.callback_query(F.data == "profile:refresh")
async def profile_refresh(callback: CallbackQuery) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_or_create_user(
            session, callback.from_user.id, callback.from_user.username
        )
        summary = await get_profile_summary(session, user.id)
    await callback.message.edit_text(_profile_text(user, summary), reply_markup=profile_refresh_kb())
    await callback.answer()
