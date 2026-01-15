import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from app.bot.handlers import (
    add_word,
    admin,
    help,
    leaderboard,
    manage_words,
    menu,
    practice,
    pronunciation,
    pronunciation_text,
    quiz,
    settings,
    start,
    stats,
)
from app.bot.middlewares.blocked import BlockedUserMiddleware
from app.config import settings as app_settings
from app.db.session import AsyncSessionLocal
from app.services.log_buffer import ErrorBufferHandler
from app.services.reminders import ReminderService
from apscheduler.schedulers.asyncio import AsyncIOScheduler

logging.basicConfig(level=app_settings.log_level)
_error_handler = ErrorBufferHandler()
_error_handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
logging.getLogger().addHandler(_error_handler)

bot = Bot(token=app_settings.bot_token)

scheduler = AsyncIOScheduler()
reminder_service = ReminderService(scheduler)


async def setup_bot_commands(bot: Bot) -> None:
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Botni ishga tushirish"),
            BotCommand(command="help", description="Yordam bo‘limi"),
            BotCommand(command="leaderboard", description="Reytinglar"),
        ],
        scope=BotCommandScopeDefault(),
    )
    if app_settings.admin_user_ids:
        admin_commands = [
            BotCommand(command="admin", description="Admin panel"),
        ]
        for admin_id in app_settings.admin_user_ids:
            await bot.set_my_commands(
                admin_commands,
                scope=BotCommandScopeChat(chat_id=admin_id),
            )


def setup_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(BlockedUserMiddleware())
    dp.include_router(admin.entry_router)
    dp.include_router(admin.menu_router)
    dp.include_router(admin.stats_router)
    dp.include_router(admin.users_router)
    dp.include_router(admin.srs_router)
    dp.include_router(admin.content_router)
    dp.include_router(admin.features_router)
    dp.include_router(admin.maintenance_router)
    dp.include_router(help.router)
    dp.include_router(leaderboard.entry_router)
    dp.include_router(leaderboard.menu_router)
    dp.include_router(leaderboard.settings_router)
    dp.include_router(leaderboard.streak_router)
    dp.include_router(leaderboard.words_router)
    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(manage_words.router)
    dp.include_router(pronunciation.router)
    dp.include_router(pronunciation_text.router)
    dp.include_router(add_word.router)
    dp.include_router(quiz.router)
    dp.include_router(practice.router)
    dp.include_router(stats.router)
    dp.include_router(settings.router)
    return dp


async def on_startup() -> None:
    await setup_bot_commands(bot)
    scheduler.start()
    async with AsyncSessionLocal() as session:
        await reminder_service.load_users(session)


async def main() -> None:
    dp = setup_dispatcher()
    await on_startup()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
