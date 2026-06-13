# backend/routers/cron.py

"""
Serverless Cron Endpoint.
Used to trigger scheduled tasks without needing a dedicated background worker like Celery.
"""

import os
from fastapi import APIRouter, Depends, HTTPException, status
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
async def run_cron_tasks(secret: str, db: AsyncSession = Depends(get_db)):
    """
    Executes all scheduled background tasks.
    Must be called with the correct `secret` query parameter matching the CRON_SECRET env var.
    """
    if secret != CRON_SECRET:
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
