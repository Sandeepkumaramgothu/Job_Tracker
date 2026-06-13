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
from fastapi.responses import FileResponse

from backend.schemas.application import FileUploadResponse
from backend.services.file_service import delete_file, get_file_path, save_file

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
    response_class=FileResponse,
)
async def download_file(filename: str) -> FileResponse:
    """
    Serves a stored file as an attachment download.
    The filename must be the server-assigned UUID-prefixed name returned
    by the upload endpoint — not the user's original filename.

    WARN: Only files within UPLOAD_DIR are served. The path-traversal guard
    in get_file_path() will raise HTTP 400 for any filename that attempts to
    escape the upload directory.
    """
    file_path = get_file_path(filename)

    # Detect media type for the Content-Type header.
    media_type, _ = mimetypes.guess_type(str(file_path))
    if media_type is None:
        media_type = "application/octet-stream"

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
