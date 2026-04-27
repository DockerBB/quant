"""APScheduler manager for background tasks."""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger


class SchedulerManager:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._started = False

    def start(self):
        if not self._started:
            self.scheduler.start()
            self._started = True

    def shutdown(self):
        if self._started:
            self.scheduler.shutdown(wait=False)
            self._started = False

    def add_job(self, func, trigger, job_id, name, **kwargs):
        return self.scheduler.add_job(
            func, trigger, id=job_id, name=name, replace_existing=True, **kwargs
        )


scheduler_manager = SchedulerManager()
