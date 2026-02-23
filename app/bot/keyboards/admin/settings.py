from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.services.i18n import b


def admin_basic_limit_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b("admin_settings.edit"), callback_data="admin:basic_limit:edit")],
            [InlineKeyboardButton(text=b("common.back"), callback_data="admin:menu")],
        ]
    )


def admin_full_test_charge_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=b("admin_settings.edit"),
                    callback_data="admin:full_test_charge:edit",
                )
            ],
            [InlineKeyboardButton(text=b("common.back"), callback_data="admin:menu")],
        ]
    )


def admin_test_limits_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=b("admin_settings.quick_count"),
                    callback_data="admin:test_limits:edit:quick_count",
                ),
                InlineKeyboardButton(
                    text=b("admin_settings.quick_time"),
                    callback_data="admin:test_limits:edit:quick_time",
                ),
            ],
            [
                InlineKeyboardButton(
                    text=b("admin_settings.full_count"),
                    callback_data="admin:test_limits:edit:full_count",
                ),
                InlineKeyboardButton(
                    text=b("admin_settings.full_time"),
                    callback_data="admin:test_limits:edit:full_time",
                ),
            ],
            [InlineKeyboardButton(text=b("common.back"), callback_data="admin:menu")],
        ]
    )


def admin_stt_provider_kb(current_provider: str) -> InlineKeyboardMarkup:
    normalized = (current_provider or "").strip().lower()
    assembly_label = b("admin_settings.stt_provider_assemblyai")
    azure_label = b("admin_settings.stt_provider_azure")
    if normalized == "assemblyai":
        assembly_label = f"✅ {assembly_label}"
    elif normalized == "azure":
        azure_label = f"✅ {azure_label}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=assembly_label,
                    callback_data="admin:stt_provider:set:assemblyai",
                ),
                InlineKeyboardButton(
                    text=azure_label,
                    callback_data="admin:stt_provider:set:azure",
                ),
            ],
            [InlineKeyboardButton(text=b("common.back"), callback_data="admin:menu")],
        ]
    )


def admin_pron_max_voice_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=b("admin_settings.edit"),
                    callback_data="admin:pron_max_voice:edit",
                )
            ],
            [InlineKeyboardButton(text=b("common.back"), callback_data="admin:menu")],
        ]
    )
