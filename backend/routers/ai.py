# backend/routers/ai.py

"""
AI extraction endpoint.

POST /api/ai/extract
  body: { job_description: str }
  returns: { job_title, company, location, salary_range, source, notes }

Uses the caller's stored AI API key (NotificationSettings.ai_api_key).
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth import get_current_user_id
from backend.database import get_db
from backend.models.application import NotificationSettings
from backend.schemas.application import AIExtractRequest, AIExtractResponse
from backend.services.ai_service import extract_fields

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post(
    "/extract",
    response_model=AIExtractResponse,
    summary="Parse a job description into structured fields",
)
async def extract(
    body: AIExtractRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> AIExtractResponse:
    result = await db.execute(
        select(NotificationSettings).where(NotificationSettings.user_id == user_id)
    )
    settings = result.scalar_one_or_none()
    if settings is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Open Settings first to save your email and paste an AI API key, "
                "then try extraction again."
            ),
        )

    parsed = await extract_fields(
        provider=settings.ai_provider,
        api_key=settings.ai_api_key,
        model=settings.ai_model,
        jd=body.job_description,
    )
    logger.info("AI extracted JD for user=%s", user_id)
    return AIExtractResponse(**parsed)
