from app.bot.handlers.leaderboard.entry import router as entry_router
from app.bot.handlers.leaderboard.menu import router as menu_router
from app.bot.handlers.leaderboard.settings import router as settings_router
from app.bot.handlers.leaderboard.streak import router as streak_router
from app.bot.handlers.leaderboard.words import router as words_router

__all__ = [
    "entry_router",
    "menu_router",
    "settings_router",
    "streak_router",
    "words_router",
]
