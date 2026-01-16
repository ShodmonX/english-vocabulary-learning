from __future__ import annotations

import logging

from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.db.repo.admin import log_admin_action
from app.db.session import AsyncSessionLocal
from app.services.db_backup.engine import cleanup_auto_backups, create_backup

logger = logging.getLogger(__name__)


def setup_backup_scheduler(scheduler) -> None:
    if not settings.auto_backup_enabled:
        logger.info("Auto backup disabled")
        return

    schedule = settings.auto_backup_schedule
    hour = settings.auto_backup_hour
    minute = settings.auto_backup_minute

    trigger = _build_trigger(schedule, hour, minute)
    if not trigger:
        logger.warning("Unsupported auto backup schedule: %s", schedule)
        return

    scheduler.add_job(
        _run_auto_backup,
        trigger=trigger,
        id="auto-backup",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    logger.info("Auto backup scheduled: %s at %02d:%02d", schedule, hour, minute)


def _build_trigger(schedule: str, hour: int, minute: int) -> CronTrigger | None:
    if schedule == "daily":
        return CronTrigger(hour=hour, minute=minute)
    if schedule == "weekly":
        return CronTrigger(day_of_week=0, hour=hour, minute=minute)
    if schedule == "monthly":
        return CronTrigger(day=1, hour=hour, minute=minute)
    return None


async def _run_auto_backup() -> None:
    try:
        info = await create_backup("auto")
        async with AsyncSessionLocal() as session:
            await log_admin_action(session, 0, "backup/auto/success", "backup", info.filename)
        deleted = await cleanup_auto_backups(settings.auto_backup_retention_days)
        async with AsyncSessionLocal() as session:
            await log_admin_action(session, 0, "backup/cleanup/success", "backup", str(deleted))
    except Exception as exc:
        logger.exception("Auto backup failed")
        async with AsyncSessionLocal() as session:
            await log_admin_action(
                session, 0, "backup/auto/fail", "backup", _truncate(str(exc))
            )


def _truncate(text: str, max_len: int = 64) -> str:
    cleaned = text.strip()
    if len(cleaned) <= max_len:
        return cleaned
    return cleaned[: max_len - 3] + "..."
