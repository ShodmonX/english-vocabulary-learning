from app.bot.handlers.admin.entry import router as entry_router
from app.bot.handlers.admin.menu import router as menu_router
from app.bot.handlers.admin.stats import router as stats_router
from app.bot.handlers.admin.users import router as users_router
from app.bot.handlers.admin.srs import router as srs_router
from app.bot.handlers.admin.content import router as content_router
from app.bot.handlers.admin.db_management import router as db_management_router
from app.bot.handlers.admin.features import router as features_router
from app.bot.handlers.admin.maintenance import router as maintenance_router

__all__ = [
    "entry_router",
    "menu_router",
    "stats_router",
    "users_router",
    "srs_router",
    "content_router",
    "db_management_router",
    "features_router",
    "maintenance_router",
]
