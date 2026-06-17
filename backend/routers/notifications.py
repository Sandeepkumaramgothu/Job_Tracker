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
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import get_current_user_id
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

async def _get_settings(
    db: AsyncSession, user_id: uuid.UUID
) -> Optional[NotificationSettings]:
    """Fetch this user's notification settings, or None if not yet created."""
    result = await db.execute(
        select(NotificationSettings).where(NotificationSettings.user_id == user_id)
    )
    return result.scalar_one_or_none()


def _to_response(settings: NotificationSettings) -> dict:
    """Convert a NotificationSettings row into the response shape, redacting
    the AI key down to a 4-char hint so it never leaves the server."""
    key = settings.ai_api_key or ""
    return {
        "id": settings.id,
        "email": settings.email,
        "notify_interview": settings.notify_interview,
        "notify_followup": settings.notify_followup,
        "notify_stale": settings.notify_stale,
        "weekly_summary": settings.weekly_summary,
        "followup_freq_days": settings.followup_freq_days,
        "ai_provider": settings.ai_provider,
        "ai_model": settings.ai_model,
        "ai_key_hint": key[-4:] if key else None,
    }


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
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> NotificationSettings:
    """
    Returns the notification preferences row.
    Returns HTTP 404 if settings have not been configured yet via PUT.
    """
    settings = await _get_settings(db, user_id)
    if settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Notification settings have not been configured yet. "
                "Send a PUT request to /api/notifications/settings to create them."
            ),
        )
    return _to_response(settings)


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
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> NotificationSettings:
    """
    Creates the settings row on first call; updates it on subsequent calls.
    All fields are replaced — this is a full replace, not a partial update.
    """
    settings = await _get_settings(db, user_id)

    if settings is None:
        settings = NotificationSettings(
            user_id=user_id,
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

    # AI fields: only overwrite when the client explicitly sent something.
    # An empty string for ai_api_key clears the stored key; None leaves it alone.
    if body.ai_provider is not None:
        settings.ai_provider = body.ai_provider or None
    if body.ai_model is not None:
        settings.ai_model = body.ai_model or None
    if body.ai_api_key is not None:
        settings.ai_api_key = body.ai_api_key or None

    await db.flush()
    await db.refresh(settings)
    return _to_response(settings)


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
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> dict:
    """
    Sends a test email to verify the current notification configuration.
    Requires settings to be configured first (HTTP 404 otherwise).

    WARN: This triggers a real email send via SendGrid or SMTP.
    Do not call this endpoint repeatedly in production — it is intended
    for one-time verification only.
    """
    settings = await _get_settings(db, user_id)
    if settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification settings not configured. Set them via PUT /api/notifications/settings first.",
        )

    try:
        await send_test_email(settings.email)
    except Exception as exc:
        logger.error("Test email failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Email send failed: {exc}. Check your SENDGRID_API_KEY and FROM_EMAIL environment variables on Render.",
        )
    logger.info("Test notification sent to %s", settings.email)
    return {"message": f"Test email sent to {settings.email}."}
