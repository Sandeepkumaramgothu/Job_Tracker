# backend/services/reminder_service.py

"""
Celery tasks for all scheduled email reminders.

Task inventory:
  send_interview_reminder  — fires 24h before interview_date
  send_followup_reminder   — fires when (today - date_applied) % followup_freq_days == 0
                             and status is 'applied' or 'followup'
  send_stale_alert         — fires when 7+ days since last timeline event and status = 'applied'
  send_weekly_summary      — fires every Monday 08:00 (scheduled via celery beat)

All tasks:
  1. Open a fresh synchronous SQLAlchemy session (Celery runs outside the
     async FastAPI context — we use the sync engine here).
  2. Read notification_settings before sending; skip silently if the
     relevant notify_* flag is False.
  3. Use the email_service async functions via asyncio.run() — acceptable
     in a Celery worker because each task runs in its own OS process/thread.

Design decision: sync SQLAlchemy (not async) is used inside Celery tasks.
Running asyncio.run() for every task would work but adds complexity with
no real benefit since Celery workers are already concurrent via processes.
The sync engine shares the same DATABASE_URL.

WARN: If DATABASE_URL uses postgresql+asyncpg:// the sync engine won't work.
We swap the scheme to postgresql+psycopg2 automatically below.
psycopg2 must be added to requirements.txt before running workers.
"""

import asyncio
import logging
import os
from datetime import date, timedelta
from typing import Optional

from celery import shared_task
from dotenv import load_dotenv
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from backend.models.application import Application, ApplicationStatus, TimelineEvent
from backend.models.application import NotificationSettings
from backend.services.email_service import (
    send_followup_reminder,
    send_interview_reminder,
    send_stale_alert,
    send_weekly_summary,
)

load_dotenv()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Synchronous engine for Celery (swap asyncpg → psycopg2)
# ---------------------------------------------------------------------------
_raw_url: str = os.environ.get(
    "DATABASE_URL", "postgresql://user:password@localhost:5432/jobtracker"
)
# WARN: asyncpg scheme is async-only; Celery tasks use a sync engine.
_sync_url: str = _raw_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")

_sync_engine = create_engine(_sync_url, pool_pre_ping=True, pool_size=5)
SyncSession = sessionmaker(bind=_sync_engine, expire_on_commit=False)


# ---------------------------------------------------------------------------
# Helper: fetch notification settings (returns None if unconfigured)
# ---------------------------------------------------------------------------
def _get_settings(db: Session) -> Optional[NotificationSettings]:
    return db.execute(select(NotificationSettings).limit(1)).scalar_one_or_none()


# ---------------------------------------------------------------------------
# Task: send_interview_reminder
# Trigger: 24h before interview_date on any timeline event with status='interview'
# ---------------------------------------------------------------------------
@shared_task(name="send_interview_reminder", bind=True, max_retries=3)
def task_send_interview_reminder(self) -> str:
    """
    Find all timeline events with interview_date = tomorrow and
    send a 24-hour reminder email for each.

    WARN: interview_date can be None on interview-status rows created before
    the validation was added. We skip those rows silently.
    """
    tomorrow = date.today() + timedelta(days=1)

    with SyncSession() as db:
        settings = _get_settings(db)
        if settings is None or not settings.notify_interview:
            logger.info("interview reminders disabled or settings not configured — skipping")
            return "skipped"

        events = db.execute(
            select(TimelineEvent)
            .where(
                TimelineEvent.status == ApplicationStatus.interview,
                TimelineEvent.interview_date == tomorrow,
            )
        ).scalars().all()

        sent = 0
        for event in events:
            app: Optional[Application] = db.get(Application, event.application_id)
            if app is None:
                continue  # application was deleted between query and fetch

            # WARN: interview_date guard — skip events missing the date
            if event.interview_date is None:
                logger.warning(
                    "TimelineEvent %s has status=interview but interview_date is None — skipping",
                    event.id,
                )
                continue

            try:
                asyncio.run(
                    send_interview_reminder(
                        to_email=settings.email,
                        company=app.company,
                        job_title=app.job_title,
                        interview_date=str(event.interview_date),
                        interview_type=event.interview_type,
                        interviewer=event.interviewer,
                    )
                )
                sent += 1
            except Exception as exc:
                logger.error("Failed to send interview reminder for event %s: %s", event.id, exc)
                raise self.retry(exc=exc, countdown=60)

    logger.info("interview_reminder: sent %d emails", sent)
    return f"sent:{sent}"


# ---------------------------------------------------------------------------
# Task: send_followup_reminder
# Trigger: (today - date_applied) % followup_freq_days == 0
#          and status in (applied, followup)
# ---------------------------------------------------------------------------
@shared_task(name="send_followup_reminder", bind=True, max_retries=3)
def task_send_followup_reminder(self) -> str:
    """
    Check every open application and fire a follow-up reminder on the
    configured cadence (default: every 7 days since date_applied).
    """
    today = date.today()

    with SyncSession() as db:
        settings = _get_settings(db)
        if settings is None or not settings.notify_followup:
            logger.info("followup reminders disabled or settings not configured — skipping")
            return "skipped"

        freq = settings.followup_freq_days

        apps = db.execute(
            select(Application).where(
                Application.status.in_(
                    [ApplicationStatus.applied, ApplicationStatus.followup]
                )
            )
        ).scalars().all()

        sent = 0
        for app in apps:
            days_since = (today - app.date_applied).days
            # WARN: integer modulo on 0 days_since would always trigger —
            # guard with days_since > 0 to avoid spamming on day-of.
            if days_since > 0 and days_since % freq == 0:
                try:
                    asyncio.run(
                        send_followup_reminder(
                            to_email=settings.email,
                            company=app.company,
                            job_title=app.job_title,
                            days_since_applied=days_since,
                        )
                    )
                    sent += 1
                except Exception as exc:
                    logger.error("Failed to send followup reminder for app %s: %s", app.id, exc)
                    raise self.retry(exc=exc, countdown=60)

    logger.info("followup_reminder: sent %d emails", sent)
    return f"sent:{sent}"


# ---------------------------------------------------------------------------
# Task: send_stale_alert
# Trigger: 7+ days since last timeline event AND status = 'applied'
# ---------------------------------------------------------------------------
@shared_task(name="send_stale_alert", bind=True, max_retries=3)
def task_send_stale_alert(self) -> str:
    """
    Find applications still in 'applied' status with no timeline update
    in 7+ days and send a stale alert.

    We use the most recent TimelineEvent.created_at as the "last update" timestamp.
    WARN: If an application has zero timeline events (data inconsistency),
    we fall back to application.created_at.
    """
    today = date.today()
    stale_threshold = timedelta(days=7)

    with SyncSession() as db:
        settings = _get_settings(db)
        if settings is None or not settings.notify_stale:
            logger.info("stale alerts disabled or settings not configured — skipping")
            return "skipped"

        apps = db.execute(
            select(Application).where(Application.status == ApplicationStatus.applied)
        ).scalars().all()

        sent = 0
        for app in apps:
            # Find most recent timeline event for this application
            last_event = db.execute(
                select(TimelineEvent)
                .where(TimelineEvent.application_id == app.id)
                .order_by(TimelineEvent.created_at.desc())
                .limit(1)
            ).scalar_one_or_none()

            last_update_date: date = (
                last_event.created_at.date() if last_event else app.created_at.date()
            )
            days_since_update = (today - last_update_date).days

            if days_since_update >= 7:
                try:
                    asyncio.run(
                        send_stale_alert(
                            to_email=settings.email,
                            company=app.company,
                            job_title=app.job_title,
                            days_since_update=days_since_update,
                        )
                    )
                    sent += 1
                except Exception as exc:
                    logger.error("Failed to send stale alert for app %s: %s", app.id, exc)
                    raise self.retry(exc=exc, countdown=60)

    logger.info("stale_alert: sent %d emails", sent)
    return f"sent:{sent}"


# ---------------------------------------------------------------------------
# Task: send_weekly_summary
# Trigger: Every Monday 08:00 via Celery beat
# ---------------------------------------------------------------------------
@shared_task(name="send_weekly_summary", bind=True, max_retries=3)
def task_send_weekly_summary(self) -> str:
    """
    Compile application counts by status and interviews scheduled this week,
    then send the Monday morning digest.
    """
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # Monday
    week_end = week_start + timedelta(days=6)

    with SyncSession() as db:
        settings = _get_settings(db)
        if settings is None or not settings.weekly_summary:
            logger.info("weekly summary disabled or settings not configured — skipping")
            return "skipped"

        all_apps = db.execute(select(Application)).scalars().all()
        total = len(all_apps)

        by_status: dict = {s.value: 0 for s in ApplicationStatus}
        for app in all_apps:
            by_status[app.status.value] += 1

        # Count interviews scheduled within this calendar week
        interviews_this_week = db.execute(
            select(TimelineEvent).where(
                TimelineEvent.status == ApplicationStatus.interview,
                TimelineEvent.interview_date >= week_start,
                TimelineEvent.interview_date <= week_end,
            )
        ).scalars().all()

        try:
            asyncio.run(
                send_weekly_summary(
                    to_email=settings.email,
                    total=total,
                    by_status=by_status,
                    interviews_this_week=len(interviews_this_week),
                )
            )
        except Exception as exc:
            logger.error("Failed to send weekly summary: %s", exc)
            raise self.retry(exc=exc, countdown=300)

    logger.info("weekly_summary: sent for %d applications", total)
    return f"sent:total={total}"
