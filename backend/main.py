# backend/main.py

"""
FastAPI application entry point.

Responsibilities:
  - Create the FastAPI app instance
  - Configure CORS
  - Register all API routers
  - Wire lifespan events (startup / shutdown logging)
  - Expose /health for container readiness probes

Start locally:
  uvicorn main:app --reload --port 8000

All routers are prefixed with /api (enforced at the router level, not here).
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import sys

# Add the project root to sys.path so 'from backend.*' absolute imports work
# when running 'uvicorn main:app' directly from the backend/ directory.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env BEFORE importing the routers — they pull in modules (auth, database)
# that read os.environ at import time. Loading after the import would leave
# those module-level vars set to None. (auth.py and database.py also call
# load_dotenv() themselves as a safety net.)
load_dotenv()

from backend.routers import ai, analytics, applications, files, notifications, cron

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown hooks
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Code before `yield` runs on startup; code after runs on shutdown.
    Use this to open/close connection pools, warm caches, etc.
    """
    logger.info("Job Tracker API starting up…")
    logger.info("Upload directory : %s", os.environ.get("UPLOAD_DIR", "./uploads"))
    logger.info("Database URL     : %s", _mask_url(os.environ.get("DATABASE_URL", "")))
    yield
    logger.info("Job Tracker API shutting down.")


def _mask_url(url: str) -> str:
    """Redact password from DATABASE_URL before logging."""
    try:
        from urllib.parse import urlparse, urlunparse
        parsed = urlparse(url)
        masked = parsed._replace(netloc=parsed.netloc.replace(parsed.password or "", "***"))
        return urlunparse(masked)
    except Exception:
        return "***"


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Job Application Tracker",
    description=(
        "Track every job application you submit — status updates, "
        "resume/cover letter uploads, interview timelines, and email reminders."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# CORS — allowed origins list
# ---------------------------------------------------------------------------

_FRONTEND_ORIGINS = [
    "http://localhost:5173",   # Vite dev server default
    "http://localhost:3000",   # CRA / fallback
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
    "https://sandeepkumaramgothu.github.io", # Your deployed GitHub Pages frontend
]

if os.environ.get("FRONTEND_URL"):
    _FRONTEND_ORIGINS.append(os.environ.get("FRONTEND_URL"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Global exception handler — ensures CORS headers are present on 500 errors.
# Without this, unhandled exceptions bypass CORS middleware, and the browser
# blocks the response entirely (shows "Network Error" instead of the real error).
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    origin = request.headers.get("origin", "")
    headers = {}
    if origin in _FRONTEND_ORIGINS:
        headers["access-control-allow-origin"] = origin
        headers["access-control-allow-credentials"] = "true"
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
        headers=headers,
    )


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(applications.router)
app.include_router(files.router)
app.include_router(notifications.router)
app.include_router(analytics.router)
app.include_router(cron.router)
app.include_router(ai.router)


# ---------------------------------------------------------------------------
# Health check — used by Docker / container orchestrators
# ---------------------------------------------------------------------------

@app.get("/health", tags=["meta"], summary="Readiness probe")
async def health_check() -> dict:
    """
    Returns 200 OK when the API process is running.
    Does NOT check DB connectivity — use /api/analytics/summary for a deeper
    liveness check that exercises the database path.
    """
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Root redirect — convenience for browser visits to /
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {"message": "Job Tracker API. Visit /docs for the interactive API reference."}
