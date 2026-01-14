from __future__ import annotations

from datetime import time

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, UserSettings
from app.db.repo.stats import get_due_count
from app.db.repo.user_settings import get_user_settings
from app.db.repo.users import get_user_by_telegram_id
from app.db.session import AsyncSessionLocal


class ReminderService:
    def __init__(self, scheduler: AsyncIOScheduler) -> None:
        self.scheduler = scheduler

    def _job_id(self, telegram_id: int) -> str:
        return f"reminder:{telegram_id}"

    def schedule_user(
        self, telegram_id: int, reminder_time: time, timezone: str
    ) -> None:
        trigger = CronTrigger(hour=reminder_time.hour, minute=reminder_time.minute, timezone=timezone)
        self.scheduler.add_job(
            self.send_reminder,
            trigger=trigger,
            id=self._job_id(telegram_id),
            replace_existing=True,
            args=[telegram_id],
        )

    def remove_user(self, telegram_id: int) -> None:
        job_id = self._job_id(telegram_id)
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)

    async def load_users(self, session: AsyncSession) -> None:
        try:
            result = await session.execute(
                select(User, UserSettings).outerjoin(
                    UserSettings, UserSettings.user_id == User.id
                )
            )
        except ProgrammingError:
            return
        for user, settings in result.all():
            enabled = settings.notifications_enabled if settings else user.reminder_enabled
            remind_time = (
                settings.notification_time if settings and settings.notification_time else user.reminder_time
            )
            if enabled and remind_time:
                self.schedule_user(user.telegram_id, remind_time, user.timezone)

    async def send_reminder(self, telegram_id: int) -> None:
        from app.main import bot  # lazy import to avoid circular dependency

        async with AsyncSessionLocal() as session:
            user = await get_user_by_telegram_id(session, telegram_id)
            if not user:
                return
            settings = await get_user_settings(session, user.id)
            enabled = settings.notifications_enabled if settings else user.reminder_enabled
            if not enabled:
                return
            due_count = await get_due_count(session, user.id)
            if due_count == 0:
                return

        await bot.send_message(
            telegram_id,
            "⏰ Mashq vaqti!\nBugun bir nechta so‘zlar sizni kutyapti 📚😉",
        )
