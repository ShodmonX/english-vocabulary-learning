from aiogram import Router

from app.bot.handlers.practice.menu import router as menu_router
from app.bot.handlers.practice.quick import router as quick_router
from app.bot.handlers.practice.recall import router as recall_router
from app.bot.handlers.practice.summary import router as summary_router

router = Router()
router.include_router(menu_router)
router.include_router(quick_router)
router.include_router(recall_router)
router.include_router(summary_router)

__all__ = ["router"]
