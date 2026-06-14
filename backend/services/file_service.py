# backend/services/file_service.py

"""
File upload handling — MIME validation, size enforcement, and S3 storage.
"""

import logging
import os
import uuid
from typing import Tuple

import aioboto3
from fastapi import HTTPException, UploadFile, status

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration — read from environment
# ---------------------------------------------------------------------------
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_ENDPOINT_URL = os.environ.get("AWS_ENDPOINT_URL")

MAX_FILE_SIZE_BYTES: int = int(os.environ.get("MAX_FILE_SIZE_MB", "5")) * 1024 * 1024

ALLOWED_MIME_TYPES: frozenset = frozenset(
    {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",
    }
)

ALLOWED_EXTENSIONS: frozenset = frozenset({".pdf", ".docx"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_file(upload: UploadFile) -> None:
    filename = upload.filename or ""
    _, suffix = os.path.splitext(filename)
    suffix = suffix.lower()
    
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"File extension '{suffix}' is not allowed. "
                "Only .pdf and .docx files are accepted."
            ),
        )
    if upload.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=(
                f"MIME type '{upload.content_type}' is not allowed. "
                "Only PDF and DOCX files are accepted."
            ),
        )

def _unique_filename(original: str) -> str:
    _, suffix = os.path.splitext(original)
    return f"{uuid.uuid4().hex}{suffix.lower()}"

def _get_s3_client():
    session = aioboto3.Session()
    return session.client(
        "s3",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        endpoint_url=AWS_ENDPOINT_URL
    )

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def save_file(upload: UploadFile) -> Tuple[str, str]:
    if not S3_BUCKET_NAME:
        raise HTTPException(
            status_code=500, detail="S3_BUCKET_NAME environment variable is not set."
        )

    _validate_file(upload)

    stored_name = _unique_filename(upload.filename or "upload")
    content = await upload.read()

    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"File size {len(content) / 1024 / 1024:.2f} MB exceeds "
                f"the limit."
            ),
        )

    try:
        async with _get_s3_client() as s3:
            await s3.put_object(
                Bucket=S3_BUCKET_NAME,
                Key=stored_name,
                Body=content,
                ContentType=upload.content_type
            )
    except Exception as exc:
        logger.error("Failed to upload file to S3: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded file. Please try again.",
        ) from exc

    logger.info("Saved upload to S3: %s (%d bytes)", stored_name, len(content))
    return stored_name, stored_name


async def delete_file(filename: str) -> None:
    if not S3_BUCKET_NAME:
        return
        
    try:
        async with _get_s3_client() as s3:
            await s3.delete_object(Bucket=S3_BUCKET_NAME, Key=filename)
        logger.info("Deleted file from S3: %s", filename)
    except Exception as exc:
        logger.error("Failed to delete file %s from S3: %s", filename, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not delete file '{filename}'.",
        ) from exc


async def get_presigned_url(filename: str) -> str:
    if not S3_BUCKET_NAME:
        raise HTTPException(status_code=500, detail="S3_BUCKET_NAME not configured.")
        
    try:
        async with _get_s3_client() as s3:
            # We add ResponseContentDisposition so it downloads as an attachment
            url = await s3.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': S3_BUCKET_NAME, 
                    'Key': filename,
                    'ResponseContentDisposition': f'attachment; filename="{filename}"'
                },
                ExpiresIn=3600
            )
            return url
    except Exception as exc:
        logger.error("Failed to generate presigned URL for %s: %s", filename, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate download link."
        ) from exc
