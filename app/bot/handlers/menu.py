from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.handlers.add_word import start_add_word_message
from app.bot.handlers.quiz import start_quiz_message
from app.bot.handlers.settings.menu import open_settings_message
from app.bot.handlers.stats import show_stats_message
from app.bot.handlers.practice.menu import practice_entry_text
from app.bot.handlers.admin.entry import open_admin_panel
from app.bot.handlers.admin.common import ensure_admin_message
from app.bot.handlers.leaderboard.menu import open_leaderboard_menu
from app.services.i18n import b

router = Router()


@router.message(F.text == b("menu.practice"))
async def menu_training(message: Message, state: FSMContext) -> None:
    await practice_entry_text(message, state)


@router.message(F.text == b("menu.quiz"))
async def menu_quiz(message: Message, state: FSMContext) -> None:
    await start_quiz_message(message, message.from_user.id, state)


@router.message(F.text == b("menu.add_word"))
async def menu_add_word(message: Message, state: FSMContext) -> None:
    await start_add_word_message(message, state)


@router.message(F.text == b("menu.stats"))
async def menu_stats(message: Message, state: FSMContext) -> None:
    await show_stats_message(message, message.from_user.id, state)


@router.message(F.text == b("menu.settings"))
async def menu_settings(message: Message, state: FSMContext) -> None:
    await open_settings_message(message, message.from_user.id, state)


@router.message(F.text == b("menu.my_words"))
async def menu_manage_words(message: Message, state: FSMContext) -> None:
    from app.bot.handlers.manage_words import open_manage_menu

    await open_manage_menu(message, state)


@router.message(F.text == b("menu.pronunciation"))
async def menu_pronunciation(message: Message, state: FSMContext) -> None:
    from app.bot.handlers.pronunciation import open_pronunciation_menu

    await open_pronunciation_menu(message, state)


@router.message(F.text == b("menu.leaderboards"))
async def menu_leaderboards(message: Message, state: FSMContext) -> None:
    await open_leaderboard_menu(message, state)


@router.message(F.text == b("menu.admin"))
async def menu_admin(message: Message, state: FSMContext) -> None:
    if not await ensure_admin_message(message):
        return
    await open_admin_panel(message, state)
