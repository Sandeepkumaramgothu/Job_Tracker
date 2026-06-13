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
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import analytics, applications, files, notifications, cron

load_dotenv()

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
# CORS
# WARN: The origins list below allows the local Vite dev server.
# For production, restrict to your actual frontend domain(s) only.
# Never use allow_origins=["*"] in production — it disables credential sharing.
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
# Routers
# ---------------------------------------------------------------------------

app.include_router(applications.router)
app.include_router(files.router)
app.include_router(notifications.router)
app.include_router(analytics.router)
app.include_router(cron.router)


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
