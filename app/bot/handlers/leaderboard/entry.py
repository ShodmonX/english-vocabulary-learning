from aiogram.filters import Command
from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.bot.handlers.leaderboard.menu import open_leaderboard_menu

router = Router()


@router.message(Command("leaderboard"))
async def leaderboard_entry(message: Message, state: FSMContext) -> None:
    await open_leaderboard_menu(message, state)
