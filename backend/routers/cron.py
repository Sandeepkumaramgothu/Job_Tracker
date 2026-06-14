# backend/routers/cron.py

"""
Serverless Cron Endpoint.
Used to trigger scheduled tasks without needing a dedicated background worker like Celery.
"""

import os
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.services.reminder_service import (
    process_followup_reminders,
    process_interview_reminders,
    process_stale_alerts,
    process_weekly_summary,
)

router = APIRouter(prefix="/api/cron", tags=["cron"])

CRON_SECRET = os.environ.get("CRON_SECRET", "default_insecure_secret")


@router.post("/run", summary="Run all scheduled tasks")
async def run_cron_tasks(
    x_cron_secret: Optional[str] = Header(default=None, alias="X-Cron-Secret"),
    secret: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    """
    Executes all scheduled background tasks.
    Prefer the `X-Cron-Secret` header. The `?secret=` query param is supported
    for backward compatibility with the existing GitHub Actions ping but
    should be migrated to the header — query strings are recorded in access logs.
    """
    supplied = x_cron_secret or secret
    if supplied != CRON_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid cron secret",
        )

    results = {}
    
    # Process all reminders sequentially
    results["interview_reminders"] = await process_interview_reminders(db)
    results["followup_reminders"] = await process_followup_reminders(db)
    results["stale_alerts"] = await process_stale_alerts(db)
    results["weekly_summary"] = await process_weekly_summary(db)

    return {"status": "ok", "results": results}
