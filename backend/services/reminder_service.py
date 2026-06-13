# backend/services/reminder_service.py

"""
Functions to process all scheduled email reminders.
These were previously Celery tasks but are now designed to be called
by a secure API endpoint (/api/cron/run) triggered by a serverless cron job.
"""

import logging
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.application import Application, ApplicationStatus, TimelineEvent
from backend.models.application import NotificationSettings
from backend.services.email_service import (
    send_followup_reminder,
    send_interview_reminder,
    send_stale_alert,
    send_weekly_summary,
)

logger = logging.getLogger(__name__)


async def _get_settings(db: AsyncSession) -> Optional[NotificationSettings]:
    result = await db.execute(select(NotificationSettings).limit(1))
    return result.scalar_one_or_none()


async def process_interview_reminders(db: AsyncSession) -> str:
    """
    Find all timeline events with interview_date = tomorrow and
    send a 24-hour reminder email for each.
    """
    tomorrow = date.today() + timedelta(days=1)
    settings = await _get_settings(db)
    
    if settings is None or not settings.notify_interview:
        logger.info("interview reminders disabled or settings not configured — skipping")
        return "skipped"

    result = await db.execute(
        select(TimelineEvent)
        .where(
            TimelineEvent.status == ApplicationStatus.interview,
            TimelineEvent.interview_date == tomorrow,
        )
    )
    events = result.scalars().all()

    sent = 0
    for event in events:
        app: Optional[Application] = await db.get(Application, event.application_id)
        if app is None or event.interview_date is None:
            continue

        try:
            await send_interview_reminder(
                to_email=settings.email,
                company=app.company,
                job_title=app.job_title,
                interview_date=str(event.interview_date),
                interview_type=event.interview_type,
                interviewer=event.interviewer,
            )
            sent += 1
        except Exception as exc:
            logger.error("Failed to send interview reminder for event %s: %s", event.id, exc)

    logger.info("interview_reminder: sent %d emails", sent)
    return f"sent:{sent}"


async def process_followup_reminders(db: AsyncSession) -> str:
    """
    Check every open application and fire a follow-up reminder on the
    configured cadence.
    """
    today = date.today()
    settings = await _get_settings(db)
    
    if settings is None or not settings.notify_followup:
        logger.info("followup reminders disabled or settings not configured — skipping")
        return "skipped"

    freq = settings.followup_freq_days

    result = await db.execute(
        select(Application).where(
            Application.status.in_(
                [ApplicationStatus.applied, ApplicationStatus.followup]
            )
        )
    )
    apps = result.scalars().all()

    sent = 0
    for app in apps:
        days_since = (today - app.date_applied).days
        if days_since > 0 and days_since % freq == 0:
            try:
                await send_followup_reminder(
                    to_email=settings.email,
                    company=app.company,
                    job_title=app.job_title,
                    days_since_applied=days_since,
                )
                sent += 1
            except Exception as exc:
                logger.error("Failed to send followup reminder for app %s: %s", app.id, exc)

    logger.info("followup_reminder: sent %d emails", sent)
    return f"sent:{sent}"


async def process_stale_alerts(db: AsyncSession) -> str:
    """
    Find applications still in 'applied' status with no timeline update
    in 7+ days and send a stale alert.
    """
    today = date.today()
    settings = await _get_settings(db)
    
    if settings is None or not settings.notify_stale:
        logger.info("stale alerts disabled or settings not configured — skipping")
        return "skipped"

    result = await db.execute(
        select(Application).where(Application.status == ApplicationStatus.applied)
    )
    apps = result.scalars().all()

    sent = 0
    for app in apps:
        # Find most recent timeline event for this application
        last_event_result = await db.execute(
            select(TimelineEvent)
            .where(TimelineEvent.application_id == app.id)
            .order_by(TimelineEvent.created_at.desc())
            .limit(1)
        )
        last_event = last_event_result.scalar_one_or_none()

        last_update_date: date = (
            last_event.created_at.date() if last_event else app.created_at.date()
        )
        days_since_update = (today - last_update_date).days

        if days_since_update >= 7:
            try:
                await send_stale_alert(
                    to_email=settings.email,
                    company=app.company,
                    job_title=app.job_title,
                    days_since_update=days_since_update,
                )
                sent += 1
            except Exception as exc:
                logger.error("Failed to send stale alert for app %s: %s", app.id, exc)

    logger.info("stale_alert: sent %d emails", sent)
    return f"sent:{sent}"


async def process_weekly_summary(db: AsyncSession) -> str:
    """
    Compile application counts by status and interviews scheduled this week,
    then send the Monday morning digest.
    """
    today = date.today()
    
    # We only want this to send on Monday
    if today.weekday() != 0:
        return "skipped (not monday)"
        
    week_start = today
    week_end = week_start + timedelta(days=6)

    settings = await _get_settings(db)
    if settings is None or not settings.weekly_summary:
        logger.info("weekly summary disabled or settings not configured — skipping")
        return "skipped"

    result = await db.execute(select(Application))
    all_apps = result.scalars().all()
    total = len(all_apps)

    by_status: dict = {s.value: 0 for s in ApplicationStatus}
    for app in all_apps:
        by_status[app.status.value] += 1

    interviews_result = await db.execute(
        select(TimelineEvent).where(
            TimelineEvent.status == ApplicationStatus.interview,
            TimelineEvent.interview_date >= week_start,
            TimelineEvent.interview_date <= week_end,
        )
    )
    interviews_this_week = interviews_result.scalars().all()

    try:
        await send_weekly_summary(
            to_email=settings.email,
            total=total,
            by_status=by_status,
            interviews_this_week=len(interviews_this_week),
        )
    except Exception as exc:
        logger.error("Failed to send weekly summary: %s", exc)

    logger.info("weekly_summary: sent for %d applications", total)
    return f"sent:total={total}"
