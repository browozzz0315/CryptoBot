from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from scheduler.jobs import push_market_summary


def configure_scheduler(application, settings) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.app.timezone)

    if settings.push.enabled:
        scheduler.add_job(
            push_market_summary,
            trigger="interval",
            minutes=settings.push.interval_minutes,
            kwargs={"application": application},
            id="market_summary_push",
            replace_existing=True,
        )

    return scheduler
