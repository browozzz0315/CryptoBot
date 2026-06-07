from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from scheduler.jobs import check_price_alerts, push_market_summary, sync_market_history


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

    if settings.history.enabled:
        scheduler.add_job(
            sync_market_history,
            trigger="interval",
            minutes=settings.history.sync_interval_minutes,
            kwargs={"application": application},
            id="market_history_sync",
            replace_existing=True,
        )

    if settings.alerts.enabled:
        scheduler.add_job(
            check_price_alerts,
            trigger="interval",
            minutes=settings.alerts.check_interval_minutes,
            kwargs={"application": application},
            id="price_alert_check",
            replace_existing=True,
        )

    return scheduler
