from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.handlers.add_word import start_add_word_message
from app.bot.handlers.quiz import start_quiz_message
from app.bot.handlers.settings.menu import open_settings_message
from app.bot.handlers.stats import show_stats_message
from app.bot.handlers.training import start_training_message

router = Router()


@router.message(F.text == "📚 Mashq qilish")
async def menu_training(message: Message, state: FSMContext) -> None:
    await start_training_message(message, message.from_user.id, state)


@router.message(F.text == "🧩 Quiz")
async def menu_quiz(message: Message, state: FSMContext) -> None:
    await start_quiz_message(message, message.from_user.id, state)


@router.message(F.text == "➕ So‘z qo‘shish")
async def menu_add_word(message: Message, state: FSMContext) -> None:
    await start_add_word_message(message, state)


@router.message(F.text == "📊 Natijalar")
async def menu_stats(message: Message, state: FSMContext) -> None:
    await show_stats_message(message, message.from_user.id, state)


@router.message(F.text == "⚙️ Sozlamalar")
async def menu_settings(message: Message, state: FSMContext) -> None:
    await open_settings_message(message, message.from_user.id, state)


@router.message(F.text == "🗂 So‘zlarim")
async def menu_manage_words(message: Message, state: FSMContext) -> None:
    from app.bot.handlers.manage_words import open_manage_menu

    await open_manage_menu(message, state)


@router.message(F.text == "🗣 Talaffuz")
async def menu_pronunciation(message: Message, state: FSMContext) -> None:
    from app.bot.handlers.pronunciation import open_pronunciation_menu

    await open_pronunciation_menu(message, state)
