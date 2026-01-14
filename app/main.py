import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import add_word, settings, start, stats, training
from app.config import settings as app_settings
from app.db.session import AsyncSessionLocal
from app.services.reminders import ReminderService
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(level=app_settings.log_level)

bot = Bot(token=app_settings.bot_token)

scheduler = AsyncIOScheduler()
reminder_service = ReminderService(scheduler)


def setup_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(start.router)
    dp.include_router(add_word.router)
    dp.include_router(training.router)
    dp.include_router(stats.router)
    dp.include_router(settings.router)
    return dp


async def on_startup() -> None:
    scheduler.start()
    async with AsyncSessionLocal() as session:
        await reminder_service.load_users(session)


async def main() -> None:
    dp = setup_dispatcher()
    await on_startup()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
