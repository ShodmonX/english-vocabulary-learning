from __future__ import annotations

from datetime import time

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.repo.stats import get_due_count
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
        result = await session.execute(select(User))
        for user in result.scalars().all():
            if user.reminder_enabled:
                self.schedule_user(user.telegram_id, user.reminder_time, user.timezone)

    async def send_reminder(self, telegram_id: int) -> None:
        from app.main import bot  # lazy import to avoid circular dependency

        async with AsyncSessionLocal() as session:
            user = await get_user_by_telegram_id(session, telegram_id)
            if not user or not user.reminder_enabled:
                return
            due_count = await get_due_count(session, user.id)
            if due_count == 0:
                return

        await bot.send_message(
            telegram_id,
            "⏰ Mashq vaqti!\nBugun bir nechta so‘zlar sizni kutyapti 📚😉",
        )
