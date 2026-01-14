from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot.keyboards.main import main_menu_kb
from app.db.repo.users import create_user, get_user_by_telegram_id
from app.db.session import AsyncSessionLocal

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    async with AsyncSessionLocal() as session:
        user = await get_user_by_telegram_id(session, message.from_user.id)
        if not user:
            user = await create_user(session, message.from_user.id)
            from app.main import reminder_service

            if user.reminder_enabled:
                reminder_service.schedule_user(
                    message.from_user.id, user.reminder_time, user.timezone
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

    await message.answer(text, reply_markup=main_menu_kb())
