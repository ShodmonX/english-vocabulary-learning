from __future__ import annotations

from dataclasses import dataclass

from app.services.i18n import t


@dataclass
class HelpContext:
    word_count: int
    due_count: int
    quiz_size: int
    notifications: bool
    notification_time: str | None
    pronunciation_enabled: bool
    pronunciation_available: bool
    translation_enabled: bool
    is_admin: bool
    streak: int


def build_help_content(ctx: HelpContext) -> dict[str, list[str]]:
    quick_start_first = (
        t("help_content.quick_start_first_empty")
        if ctx.word_count == 0
        else t("help_content.quick_start_first_default")
    )
    pron_status = (
        t("help_content.status_on")
        if ctx.pronunciation_available
        else t("help_content.status_off")
    )
    pron_user_status = (
        t("help_content.enabled") if ctx.pronunciation_enabled else t("help_content.disabled")
    )
    translation_status = (
        t("help_content.enabled") if ctx.translation_enabled else t("help_content.disabled")
    )
    streak_line = (
        t("help_content.streak_line", streak=ctx.streak)
        if ctx.streak >= 1
        else t("help_content.streak_none")
    )
    notif_line = (
        t("help_content.notification_line", time=ctx.notification_time or t("common.none"))
        if ctx.notifications
        else t("help_content.notification_off")
    )

    return {
        "quick": [
            t(
                "help_content.quick",
                quick_start_first=quick_start_first,
                streak_line=streak_line,
            )
        ],
        "add": [t("help_content.add")],
        "srs": [
            t(
                "help_content.srs",
                due_count=ctx.due_count,
            )
        ],
        "quiz": [t("help_content.quiz", quiz_size=ctx.quiz_size)],
        "pron": [
            t(
                "help_content.pron",
                pron_status=pron_status,
                pron_user_status=pron_user_status,
            )
        ],
        "words": [t("help_content.words")],
        "settings": [
            t(
                "help_content.settings",
                quiz_size=ctx.quiz_size,
                translation_status=translation_status,
                notif_line=notif_line,
            )
        ],
        "trouble": [t("help_content.trouble")],
        "privacy": [t("help_content.privacy")],
        "admin": [t("help_content.admin")],
    }
