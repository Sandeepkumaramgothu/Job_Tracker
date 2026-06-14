# backend/routers/files.py

"""
File upload and download endpoints.

Routes:
  POST  /api/files/upload       — multipart upload; returns { filename, path }
  GET   /api/files/{filename}   — serve file as a download (Content-Disposition: attachment)
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status

from backend.auth import get_current_user_id
from backend.schemas.application import FileUploadResponse
from backend.services.file_service import get_presigned_url, save_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/files", tags=["files"])


# ---------------------------------------------------------------------------
# POST /api/files/upload
# ---------------------------------------------------------------------------

@router.post(
    "/upload",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a resume or cover letter (PDF or DOCX, max 5 MB)",
)
async def upload_file(
    file: UploadFile = File(..., description="PDF or DOCX file, max 5 MB"),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> FileUploadResponse:
    """
    Accepts a single file upload via multipart/form-data.
    Validates MIME type (PDF / DOCX only) and enforces a 5 MB size limit.
    Returns the stored filename and absolute path for linking to an application.

    The stored S3 key is prefixed with the user's id so download authorization
    can confirm ownership without a separate DB lookup.
    """
    stored_name, stored_path = await save_file(file, key_prefix=str(user_id))
    return FileUploadResponse(filename=stored_name, path=stored_path)


# ---------------------------------------------------------------------------
# GET /api/files/{filename}
# ---------------------------------------------------------------------------

@router.get(
    "/{filename:path}",
    summary="Get a short-lived presigned URL for a stored file",
)
async def get_file_download_url(
    filename: str,
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> dict:
    """
    Returns a presigned S3 URL the client can open to download the file.

    Returns JSON (not a 307) because the auth header from the browser would be
    stripped on a redirect, and an <a href> on this endpoint can't carry the
    Authorization header. The frontend fetches this via axios then opens the
    URL with window.open.

    Authorization is enforced by the key prefix: the upload endpoint writes
    files under `<user_id>/<random>.<ext>`, so a user can only get URLs for
    files whose key starts with their own user id.
    """
    if not filename.startswith(f"{user_id}/"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found.",
        )
    url = await get_presigned_url(filename)
    return {"url": url}
