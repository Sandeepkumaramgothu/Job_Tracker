# backend/routers/notifications.py

"""
Notification settings endpoints.

Routes:
  GET   /api/notifications/settings   — get current notification preferences
  PUT   /api/notifications/settings   — create or replace notification preferences
  POST  /api/notifications/test       — send a test email to the configured address

Design decision: the notification_settings table holds a single row per
deployment (not per user — this tracker is single-user). GET returns the
first row if it exists, or HTTP 404 if not yet configured. PUT upserts:
updates the existing row if found, otherwise inserts a new one.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.application import NotificationSettings
from backend.schemas.application import (
    NotificationSettingsResponse,
    NotificationSettingsUpdate,
)
from backend.services.email_service import send_test_email

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def _get_settings(db: AsyncSession) -> Optional[NotificationSettings]:
    """Fetch the single notification settings row, or None if not yet created."""
    result = await db.execute(select(NotificationSettings).limit(1))
    return result.scalar_one_or_none()


# ---------------------------------------------------------------------------
# GET /api/notifications/settings
# ---------------------------------------------------------------------------

@router.get(
    "/settings",
    response_model=NotificationSettingsResponse,
    summary="Get current notification preferences",
)
async def get_notification_settings(
    db: AsyncSession = Depends(get_db),
) -> NotificationSettings:
    """
    Returns the notification preferences row.
    Returns HTTP 404 if settings have not been configured yet via PUT.
    """
    settings = await _get_settings(db)
    if settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Notification settings have not been configured yet. "
                "Send a PUT request to /api/notifications/settings to create them."
            ),
        )
    return settings


# ---------------------------------------------------------------------------
# PUT /api/notifications/settings
# ---------------------------------------------------------------------------

@router.put(
    "/settings",
    response_model=NotificationSettingsResponse,
    summary="Save (upsert) notification preferences",
)
async def upsert_notification_settings(
    body: NotificationSettingsUpdate,
    db: AsyncSession = Depends(get_db),
) -> NotificationSettings:
    """
    Creates the settings row on first call; updates it on subsequent calls.
    All fields are replaced — this is a full replace, not a partial update.
    """
    settings = await _get_settings(db)

    if settings is None:
        settings = NotificationSettings(
            email=body.email,
            notify_interview=body.notify_interview,
            notify_followup=body.notify_followup,
            notify_stale=body.notify_stale,
            weekly_summary=body.weekly_summary,
            followup_freq_days=body.followup_freq_days,
        )
        db.add(settings)
        logger.info("Created notification settings for %s", body.email)
    else:
        settings.email = body.email
        settings.notify_interview = body.notify_interview
        settings.notify_followup = body.notify_followup
        settings.notify_stale = body.notify_stale
        settings.weekly_summary = body.weekly_summary
        settings.followup_freq_days = body.followup_freq_days
        logger.info("Updated notification settings for %s", body.email)

    await db.flush()
    await db.refresh(settings)
    return settings


# ---------------------------------------------------------------------------
# POST /api/notifications/test
# ---------------------------------------------------------------------------

@router.post(
    "/test",
    status_code=status.HTTP_200_OK,
    summary="Send a test email to the configured notification address",
)
async def send_test_notification(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Sends a test email to verify the current notification configuration.
    Requires settings to be configured first (HTTP 404 otherwise).

    WARN: This triggers a real email send via SendGrid or SMTP.
    Do not call this endpoint repeatedly in production — it is intended
    for one-time verification only.
    """
    settings = await _get_settings(db)
    if settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification settings not configured. Set them via PUT /api/notifications/settings first.",
        )

    await send_test_email(settings.email)
    logger.info("Test notification sent to %s", settings.email)
    return {"message": f"Test email sent to {settings.email}."}
