from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b


def admin_admins_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("admin_admins.add"), callback_data="admin:admins:add")],
            [InlineKeyboardButton(text=b("admin_admins.list"), callback_data="admin:admins:list")],
            [InlineKeyboardButton(text=b("common.back"), callback_data="admin:menu")],
        ]
    )


def admin_admins_add_method_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("admin_admins.add_id"), callback_data="admin:admins:add:id")],
            [InlineKeyboardButton(text=b("admin_admins.add_forward"), callback_data="admin:admins:add:forward")],
            [InlineKeyboardButton(text=b("common.back"), callback_data="admin:admins")],
        ]
    )


def admin_admins_list_kb(items: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"admin:admins:view:{admin_id}")]
        for admin_id, label in items
    ]
    rows.append([InlineKeyboardButton(text=b("common.back"), callback_data="admin:admins")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_admin_detail_kb(is_owner: bool, admin_id: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if not is_owner:
        rows.append(
            [
                InlineKeyboardButton(
                    text=b("admin_admins.remove"),
                    callback_data=f"admin:admins:remove:{admin_id}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text=b("common.back"), callback_data="admin:admins:list")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_admin_add_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=b("common.confirm_yes"), callback_data="admin:admins:add:confirm"),
                InlineKeyboardButton(text=b("common.confirm_no"), callback_data="admin:admins:add:cancel"),
            ]
        ]
    )


def admin_admin_remove_confirm_kb(admin_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=b("common.confirm_yes"),
                    callback_data=f"admin:admins:remove_confirm:{admin_id}",
                ),
                InlineKeyboardButton(
                    text=b("common.confirm_no"),
                    callback_data=f"admin:admins:view:{admin_id}",
                ),
            ]
        ]
    )


def admin_admins_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=b("common.confirm_no"),
                    callback_data="admin:admins",
                )
            ]
        ]
    )
