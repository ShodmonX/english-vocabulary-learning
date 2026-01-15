from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.keyboards.main import main_menu_kb
from app.db.repo.user_settings import get_or_create_user_settings
from app.config import settings
from app.db.repo.users import create_user, get_user_by_telegram_id
from app.db.session import AsyncSessionLocal

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
            text = (
                "👋 Assalomu alaykum! Ingliz tilini o‘rganishni bugun boshlaymizmi? 🇬🇧✨\n"
                "Keling, har kuni oz-ozdan, lekin samarali o‘rganamiz!\n"
                "Pastdagi menyudan mashqni boshlang yoki yangi so‘z qo‘shing."
            )
        else:
            text = (
                "👋 Assalomu alaykum! Qaytganingizdan xursandman.\n"
                "Quyidagi menyudan davom etishni tanlang 😊"
            )

    is_admin = message.from_user.id in settings.admin_user_ids
    await message.answer(
        text,
        reply_markup=main_menu_kb(is_admin=is_admin, streak=user.current_streak),
    )


async def _notify_admins_new_user(message: Message, telegram_id: int) -> None:
    if not settings.admin_user_ids:
        return
    username = message.from_user.username or "—"
    full_name = message.from_user.full_name or "—"
    text = (
        "🆕 Yangi user /start bosdi\n"
        f"ID: {telegram_id}\n"
        f"Username: @{username}\n"
        f"Full name: {full_name}"
    )
    for admin_id in settings.admin_user_ids:
        try:
            await message.bot.send_message(admin_id, text)
        except Exception:
            continue
