from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b


def admin_packages_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=b("admin_packages.edit_basic"), callback_data="admin:packages:edit:BASIC"),
                InlineKeyboardButton(text=b("admin_packages.edit_standard"), callback_data="admin:packages:edit:STANDARD"),
                InlineKeyboardButton(text=b("admin_packages.edit_pro"), callback_data="admin:packages:edit:PRO"),
            ],
            [InlineKeyboardButton(text=b("common.back"), callback_data="admin:menu")],
        ]
    )


def admin_package_edit_kb(package_key: str, is_active: bool) -> InlineKeyboardMarkup:
    toggle_label = (
        b("admin_packages.deactivate") if is_active else b("admin_packages.activate")
    )
    toggle_value = "off" if is_active else "on"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=b("admin_packages.edit_seconds"),
                    callback_data=f"admin:packages:seconds:{package_key}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=b("admin_packages.edit_manual"),
                    callback_data=f"admin:packages:manual:{package_key}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=b("admin_packages.edit_stars"),
                    callback_data=f"admin:packages:stars:{package_key}",
                )
            ],
            [
                InlineKeyboardButton(
                    text=toggle_label,
                    callback_data=f"admin:packages:toggle:{package_key}:{toggle_value}",
                )
            ],
            [InlineKeyboardButton(text=b("common.back"), callback_data="admin:packages")],
        ]
    )
