from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards.main import main_menu_kb
from app.db.repo.user_settings import get_or_create_user_settings
from app.config import settings
from app.db.repo.users import create_user, get_user_by_telegram_id
from app.db.session import AsyncSessionLocal
from app.services.i18n import t

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            user = await create_user(
                session,
                message.from_user.id,
                username=message.from_user.username,
            )
            await _notify_admins_new_user(message, user.telegram_id)
        user_settings = await get_or_create_user_settings(session, user)
        from app.main import reminder_service

        if user_settings.notifications_enabled and user_settings.notification_time:
            reminder_service.schedule_user(
                message.from_user.id, user_settings.notification_time, user.timezone
            )
            text = t("start.welcome_notifications")
        else:
            text = t("start.welcome_default")

    is_admin = message.from_user.id in settings.admin_user_ids
    await message.answer(
        text,
        reply_markup=main_menu_kb(is_admin=is_admin, streak=user.current_streak),
    )


async def _notify_admins_new_user(message: Message, telegram_id: int) -> None:
    if not settings.admin_user_ids:
        return
    username = message.from_user.username or t("common.none")
    full_name = message.from_user.full_name or t("common.none")
    text = t(
        "admin.new_user",
        telegram_id=telegram_id,
        username=username,
        full_name=full_name,
    )
    for admin_id in settings.admin_user_ids:
        try:
            await message.bot.send_message(admin_id, text)
        except Exception:
            continue
