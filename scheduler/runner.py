from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from scheduler.jobs import (
    check_price_alerts,
    check_subscription_events,
    push_market_summary,
    push_strategy_radar,
    send_no_event_summary,
    sync_market_history,
)


def configure_scheduler(application, settings) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=settings.app.timezone)

    if settings.push.enabled:
        _add_scheduled_job(
            scheduler=scheduler,
            job_func=push_market_summary,
            job_id="market_summary_push",
            application=application,
            schedule_mode=settings.push.schedule_mode,
            interval_minutes=settings.push.interval_minutes,
            cron_hours=settings.push.cron_hours,
            cron_minute=settings.push.cron_minute,
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

    if settings.subscription_events.enabled:
        scheduler.add_job(
            check_subscription_events,
            trigger="interval",
            minutes=settings.subscription_events.check_interval_minutes,
            kwargs={"application": application},
            id="subscription_event_check",
            replace_existing=True,
        )
        if settings.subscription_events.no_event_summary_enabled and settings.subscription_events.no_event_summary_hours:
            scheduler.add_job(
                send_no_event_summary,
                trigger="cron",
                hour=",".join(str(hour) for hour in settings.subscription_events.no_event_summary_hours),
                minute=settings.subscription_events.no_event_summary_minute,
                kwargs={"application": application},
                id="subscription_no_event_summary",
                replace_existing=True,
            )

    if settings.radar.enabled and settings.radar.schedule_enabled:
        _add_scheduled_job(
            scheduler=scheduler,
            job_func=push_strategy_radar,
            job_id="strategy_radar_push",
            application=application,
            schedule_mode=settings.radar.schedule_mode,
            interval_minutes=settings.radar.interval_minutes,
            cron_hours=settings.radar.cron_hours,
            cron_minute=settings.radar.cron_minute,
        )

    return scheduler


def _add_scheduled_job(
    *,
    scheduler: AsyncIOScheduler,
    job_func,
    job_id: str,
    application,
    schedule_mode: str,
    interval_minutes: int,
    cron_hours: list[int],
    cron_minute: int,
) -> None:
    if schedule_mode == "cron" and cron_hours:
        scheduler.add_job(
            job_func,
            trigger="cron",
            hour=",".join(str(hour) for hour in cron_hours),
            minute=cron_minute,
            kwargs={"application": application},
            id=job_id,
            replace_existing=True,
        )
        return

    scheduler.add_job(
        job_func,
        trigger="interval",
        minutes=interval_minutes,
        kwargs={"application": application},
        id=job_id,
        replace_existing=True,
    )
