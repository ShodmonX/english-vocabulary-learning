from app.bot.keyboards.admin.main import admin_back_kb, admin_menu_kb
from app.bot.keyboards.admin.users import admin_confirm_kb, admin_user_actions_kb, admin_users_menu_kb
from app.bot.keyboards.admin.features import admin_features_kb
from app.bot.keyboards.admin.content import admin_content_detail_kb, admin_content_list_kb, admin_content_menu_kb
from app.bot.keyboards.admin.maintenance import admin_maintenance_kb
from app.bot.keyboards.admin.srs import admin_srs_reset_kb

__all__ = [
    "admin_back_kb",
    "admin_menu_kb",
    "admin_users_menu_kb",
    "admin_user_actions_kb",
    "admin_confirm_kb",
    "admin_features_kb",
    "admin_content_menu_kb",
    "admin_content_list_kb",
    "admin_content_detail_kb",
    "admin_maintenance_kb",
    "admin_srs_reset_kb",
]
