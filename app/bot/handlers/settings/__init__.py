from aiogram import Router

from app.bot.handlers.settings.advanced import router as advanced_router
from app.bot.handlers.settings.language import router as language_router
from app.bot.handlers.settings.learning import router as learning_router
from app.bot.handlers.settings.menu import router as menu_router
from app.bot.handlers.settings.notifications import router as notifications_router
from app.bot.handlers.settings.tests import router as tests_router

router = Router()
router.include_router(menu_router)
router.include_router(learning_router)
router.include_router(tests_router)
router.include_router(language_router)
router.include_router(notifications_router)
router.include_router(advanced_router)

__all__ = ["router"]
