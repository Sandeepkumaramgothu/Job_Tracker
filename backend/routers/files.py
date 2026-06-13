# backend/routers/files.py

"""
File upload and download endpoints.

Routes:
  POST  /api/files/upload       — multipart upload; returns { filename, path }
  GET   /api/files/{filename}   — serve file as a download (Content-Disposition: attachment)
"""

import logging
import mimetypes

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import RedirectResponse

from backend.schemas.application import FileUploadResponse
from backend.services.file_service import delete_file, get_presigned_url, save_file

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
) -> FileUploadResponse:
    """
    Accepts a single file upload via multipart/form-data.
    Validates MIME type (PDF / DOCX only) and enforces a 5 MB size limit.
    Returns the stored filename and absolute path for linking to an application.

    Workflow:
      1. Upload the file via this endpoint → receive { filename, path }
      2. PATCH /api/applications/{id} with { resume_path: path } or { cover_path: path }
    """
    stored_name, stored_path = await save_file(file)
    return FileUploadResponse(filename=stored_name, path=stored_path)


# ---------------------------------------------------------------------------
# GET /api/files/{filename}
# ---------------------------------------------------------------------------

@router.get(
    "/{filename}",
    summary="Download a stored file by filename",
    response_class=RedirectResponse,
)
async def download_file(filename: str) -> RedirectResponse:
    """
    Redirects to an S3 presigned URL to securely download the file directly 
    from cloud storage.
    """
    url = await get_presigned_url(filename)
    # Temporary redirect so the browser doesn't cache the short-lived presigned URL
    return RedirectResponse(url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
