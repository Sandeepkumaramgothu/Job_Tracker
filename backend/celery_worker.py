# backend/celery_worker.py

"""
Celery application definition and beat schedule.

Start the worker (with beat scheduler) from the backend/ directory:
  celery -A celery_worker worker --beat --loglevel=info

Beat schedule (all times UTC):
  interview_reminder   — daily at 08:00 UTC
  followup_reminder    — daily at 09:00 UTC
  stale_alert          — daily at 09:30 UTC
  weekly_summary       — every Monday at 08:00 UTC

Design decision: all four tasks run on a daily/weekly cron rather than being
triggered on demand. This keeps the architecture simple — tasks query the DB
themselves to decide what to send. An alternative (event-driven triggers per
application) would be more precise but adds significant complexity.
"""

import os

from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Celery app
# ---------------------------------------------------------------------------
REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "jobtracker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["backend.services.reminder_service"],
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Timezone — all cron times are UTC
    timezone="UTC",
    enable_utc=True,

    # Reliability
    task_acks_late=True,          # acknowledge after task completes, not before
    worker_prefetch_multiplier=1, # one task at a time per worker process

    # Result expiry — keep results for 24h then discard
    result_expires=86400,

    # Beat schedule
    beat_schedule={
        "interview-reminder-daily": {
            "task": "send_interview_reminder",
            "schedule": crontab(hour=8, minute=0),       # 08:00 UTC daily
            "options": {"expires": 3600},                # drop if not consumed in 1h
        },
        "followup-reminder-daily": {
            "task": "send_followup_reminder",
            "schedule": crontab(hour=9, minute=0),       # 09:00 UTC daily
            "options": {"expires": 3600},
        },
        "stale-alert-daily": {
            "task": "send_stale_alert",
            "schedule": crontab(hour=9, minute=30),      # 09:30 UTC daily
            "options": {"expires": 3600},
        },
        "weekly-summary-monday": {
            "task": "send_weekly_summary",
            "schedule": crontab(hour=8, minute=0, day_of_week=1),  # Monday 08:00 UTC
            "options": {"expires": 7200},
        },
    },
)
