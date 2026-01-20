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
    profile,
    word_selection,
)
from app.bot.middlewares.blocked import BlockedUserMiddleware
from app.bot.middlewares.ignore_not_modified import IgnoreNotModifiedMiddleware
from app.config import settings as app_settings
from app.db.session import AsyncSessionLocal
from app.db.repo.stars_payments import reprocess_paid
from app.db.repo.bot_admins import ensure_owner_admin, list_admins, upsert_admin
from app.db.repo.users import get_user_by_telegram_id
from app.bot.handlers.admin.common import get_main_admin_id
from app.services.log_buffer import ErrorBufferHandler
from app.services.reminders import ReminderService
from app.services.db_backup.scheduler import setup_backup_scheduler
from app.services.i18n import load_locales, t
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
            BotCommand(command="start", description=t("commands.start")),
            BotCommand(command="help", description=t("commands.help")),
            BotCommand(command="leaderboard", description=t("commands.leaderboard")),
            BotCommand(command="profile", description=t("commands.profile")),
        ],
        scope=BotCommandScopeDefault(),
    )
    if app_settings.admin_user_ids:
        admin_commands = [
            BotCommand(command="admin", description=t("commands.admin")),
            BotCommand(command="addcredit", description=t("commands.addcredit")),
            BotCommand(command="addadmin", description=t("commands.addadmin")),
        ]
        for admin_id in app_settings.admin_user_ids:
            await bot.set_my_commands(
                admin_commands,
                scope=BotCommandScopeChat(chat_id=admin_id),
            )


def setup_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(BlockedUserMiddleware())
    dp.update.middleware(IgnoreNotModifiedMiddleware())
    dp.include_router(admin.entry_router)
    dp.include_router(admin.menu_router)
    dp.include_router(admin.stats_router)
    dp.include_router(admin.users_router)
    dp.include_router(admin.srs_router)
    dp.include_router(admin.content_router)
    dp.include_router(admin.db_management_router)
    dp.include_router(admin.features_router)
    dp.include_router(admin.maintenance_router)
    dp.include_router(admin.credits_router)
    dp.include_router(admin.packages_router)
    dp.include_router(admin.contact_router)
    dp.include_router(admin.admins_router)
    dp.include_router(admin.settings_router)
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
    dp.include_router(profile.router)
    dp.include_router(add_word.router)
    dp.include_router(quiz.router)
    dp.include_router(word_selection.router)
    dp.include_router(practice.router)
    dp.include_router(stats.router)
    dp.include_router(settings.router)
    return dp


async def on_startup() -> None:
    load_locales()
    await setup_bot_commands(bot)
    setup_backup_scheduler(scheduler)
    scheduler.start()
    async with AsyncSessionLocal() as session:
        owner_id = get_main_admin_id()
        if owner_id:
            owner_name = str(owner_id)
            owner_username = None
            try:
                chat = await bot.get_chat(owner_id)
                owner_name = chat.first_name or chat.username or owner_name
                owner_username = chat.username
            except Exception:
                pass
            await ensure_owner_admin(session, owner_id, owner_name, owner_username)
            for admin_id in list(app_settings.admin_user_ids):
                if admin_id == owner_id:
                    continue
                user = await get_user_by_telegram_id(session, admin_id)
                first_name = user.username if user and user.username else str(admin_id)
                await upsert_admin(session, admin_id, first_name, user.username if user else None, owner_id)
            admins = await list_admins(session)
            app_settings.admin_user_ids.update({admin.tg_user_id for admin in admins})
            app_settings.admin_user_ids.add(owner_id)
        await reminder_service.load_users(session)
        await reprocess_paid(session)


async def main() -> None:
    dp = setup_dispatcher()
    await on_startup()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
