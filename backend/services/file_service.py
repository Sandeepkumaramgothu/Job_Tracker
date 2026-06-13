# backend/services/file_service.py

"""
File upload handling — MIME validation, size enforcement, and storage abstraction.

Design decision: files are stored on local disk under UPLOAD_DIR (default ./uploads).
The abstraction layer (save_file / delete_file) is kept intentionally thin so it can
be swapped out for an S3 implementation without touching router code.
Callers always work with `str` paths (local disk paths or S3 keys).

WARN: This service does NOT clean up stale DB file-path references if a disk
delete fails. The router must handle that case explicitly.
"""

import logging
import os
import uuid
from pathlib import Path
from typing import Tuple

import aiofiles
from fastapi import HTTPException, UploadFile, status

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration — read from environment, with safe defaults
# ---------------------------------------------------------------------------
UPLOAD_DIR: Path = Path(os.environ.get("UPLOAD_DIR", "./uploads")).resolve()
MAX_FILE_SIZE_BYTES: int = int(os.environ.get("MAX_FILE_SIZE_MB", "5")) * 1024 * 1024

# Allowed MIME types as required by CLAUDE.md:
#   PDF and DOCX only.
# WARN: Browsers sometimes send 'application/octet-stream' for .docx — we
# also accept the Microsoft OOXML type to cover that edge case.
ALLOWED_MIME_TYPES: frozenset = frozenset(
    {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/octet-stream",  # fallback some browsers send for .docx
    }
)

ALLOWED_EXTENSIONS: frozenset = frozenset({".pdf", ".docx"})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_file(upload: UploadFile) -> None:
    """
    Validate MIME type and file extension.
    Raises HTTP 415 if the file type is not allowed.

    WARN: MIME type reported by the client can be spoofed.
    For production hardening, add python-magic to inspect the file's
    actual magic bytes. This implementation trusts the Content-Type header
    and the file extension, which is acceptable for an internal tool.
    """
    suffix = Path(upload.filename or "").suffix.lower()
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


def _ensure_upload_dir() -> None:
    """Create the upload directory if it does not already exist."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _unique_filename(original: str) -> str:
    """
    Prefix the original filename with a UUID4 to prevent collisions and
    avoid directory traversal attacks via crafted filenames.
    """
    suffix = Path(original).suffix.lower()
    return f"{uuid.uuid4().hex}{suffix}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def save_file(upload: UploadFile) -> Tuple[str, str]:
    """
    Validate, read, and persist an uploaded file to UPLOAD_DIR.

    Returns:
        (stored_filename, absolute_path_str)

    Raises:
        HTTP 415 — unsupported file type
        HTTP 413 — file exceeds MAX_FILE_SIZE_BYTES
        HTTP 500 — disk write failure
    """
    _validate_file(upload)
    _ensure_upload_dir()

    stored_name = _unique_filename(upload.filename or "upload")
    dest_path = UPLOAD_DIR / stored_name

    try:
        content = await upload.read()

        if len(content) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"File size {len(content) / 1024 / 1024:.2f} MB exceeds "
                    f"the {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB limit."
                ),
            )

        async with aiofiles.open(dest_path, "wb") as f:
            await f.write(content)

    except HTTPException:
        raise
    except OSError as exc:
        logger.error("Failed to write uploaded file to %s: %s", dest_path, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded file. Please try again.",
        ) from exc

    logger.info("Saved upload: %s (%d bytes)", dest_path, len(content))
    return stored_name, str(dest_path)


async def delete_file(filename: str) -> None:
    """
    Delete a stored file by its stored filename (not a full path).

    WARN: If the file does not exist on disk this is treated as a no-op
    (the DB record may already be stale — log a warning but don't raise).
    """
    target = UPLOAD_DIR / filename
    if not target.exists():
        logger.warning("delete_file: file not found on disk: %s", target)
        return
    try:
        target.unlink()
        logger.info("Deleted file: %s", target)
    except OSError as exc:
        logger.error("Failed to delete file %s: %s", target, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not delete file '{filename}'.",
        ) from exc


def get_file_path(filename: str) -> Path:
    """
    Resolve and validate the full path for a stored filename.

    Raises:
        HTTP 404 — file not found on disk
        HTTP 400 — attempted path traversal outside UPLOAD_DIR

    WARN: Always use this function before serving files — never construct
    paths from user input directly. The resolve() + is_relative_to() guard
    prevents directory traversal attacks.
    """
    target = (UPLOAD_DIR / filename).resolve()

    # Guard against path traversal (e.g. filename = "../../etc/passwd")
    if not target.is_relative_to(UPLOAD_DIR):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename.",
        )

    if not target.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File '{filename}' not found.",
        )

    return target
