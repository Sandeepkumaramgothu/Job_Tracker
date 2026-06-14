# backend/services/reminder_service.py

"""
Scheduled email reminder processors.

Called by /api/cron/run (triggered by a GitHub Action cron job).
Multi-tenant: each function iterates over every user's NotificationSettings
row and processes that user's reminders independently.
"""

import logging
import uuid
from datetime import date, timedelta
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.application import (
    Application,
    ApplicationStatus,
    NotificationSettings,
    TimelineEvent,
)
from backend.services.email_service import (
    send_followup_reminder,
    send_interview_reminder,
    send_stale_alert,
    send_weekly_summary,
)

logger = logging.getLogger(__name__)


async def _all_settings(db: AsyncSession) -> List[NotificationSettings]:
    """Fetch every user's notification settings."""
    result = await db.execute(select(NotificationSettings))
    return list(result.scalars().all())


async def process_interview_reminders(db: AsyncSession) -> str:
    """24-hour interview reminders, fanned out per user."""
    tomorrow = date.today() + timedelta(days=1)
    total_sent = 0
    for settings in await _all_settings(db):
        if not settings.notify_interview:
            continue

        result = await db.execute(
            select(TimelineEvent)
            .join(Application, Application.id == TimelineEvent.application_id)
            .where(
                Application.user_id == settings.user_id,
                TimelineEvent.status == ApplicationStatus.interview,
                TimelineEvent.interview_date == tomorrow,
            )
        )
        events = result.scalars().all()

        for event in events:
            app = await db.get(Application, event.application_id)
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
                total_sent += 1
            except Exception as exc:
                logger.error(
                    "interview reminder failed user=%s event=%s: %s",
                    settings.user_id, event.id, exc,
                )

    logger.info("interview_reminder: sent %d emails", total_sent)
    return f"sent:{total_sent}"


async def process_followup_reminders(db: AsyncSession) -> str:
    """Fire follow-up reminders on each user's configured cadence."""
    today = date.today()
    total_sent = 0
    for settings in await _all_settings(db):
        if not settings.notify_followup:
            continue

        result = await db.execute(
            select(Application).where(
                Application.user_id == settings.user_id,
                Application.status.in_(
                    [ApplicationStatus.applied, ApplicationStatus.followup]
                ),
            )
        )
        apps = result.scalars().all()

        for app in apps:
            days_since = (today - app.date_applied).days
            if days_since > 0 and days_since % settings.followup_freq_days == 0:
                try:
                    await send_followup_reminder(
                        to_email=settings.email,
                        company=app.company,
                        job_title=app.job_title,
                        days_since_applied=days_since,
                    )
                    total_sent += 1
                except Exception as exc:
                    logger.error(
                        "followup reminder failed user=%s app=%s: %s",
                        settings.user_id, app.id, exc,
                    )

    logger.info("followup_reminder: sent %d emails", total_sent)
    return f"sent:{total_sent}"


async def process_stale_alerts(db: AsyncSession) -> str:
    """Alert on applications stuck in 'applied' with no update in 7+ days."""
    today = date.today()
    total_sent = 0
    for settings in await _all_settings(db):
        if not settings.notify_stale:
            continue

        result = await db.execute(
            select(Application).where(
                Application.user_id == settings.user_id,
                Application.status == ApplicationStatus.applied,
            )
        )
        apps = result.scalars().all()

        for app in apps:
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
                    total_sent += 1
                except Exception as exc:
                    logger.error(
                        "stale alert failed user=%s app=%s: %s",
                        settings.user_id, app.id, exc,
                    )

    logger.info("stale_alert: sent %d emails", total_sent)
    return f"sent:{total_sent}"


async def process_weekly_summary(db: AsyncSession) -> str:
    """Monday morning digest, per user."""
    today = date.today()
    if today.weekday() != 0:
        return "skipped (not monday)"

    week_start = today
    week_end = week_start + timedelta(days=6)
    total_sent = 0

    for settings in await _all_settings(db):
        if not settings.weekly_summary:
            continue

        result = await db.execute(
            select(Application).where(Application.user_id == settings.user_id)
        )
        all_apps = result.scalars().all()
        total = len(all_apps)

        by_status = {s.value: 0 for s in ApplicationStatus}
        for app in all_apps:
            by_status[app.status.value] += 1

        interviews_result = await db.execute(
            select(TimelineEvent)
            .join(Application, Application.id == TimelineEvent.application_id)
            .where(
                Application.user_id == settings.user_id,
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
            total_sent += 1
        except Exception as exc:
            logger.error(
                "weekly summary failed user=%s: %s", settings.user_id, exc,
            )

    logger.info("weekly_summary: sent %d emails", total_sent)
    return f"sent:{total_sent}"
