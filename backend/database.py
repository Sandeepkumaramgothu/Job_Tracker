# backend/database.py
from __future__ import annotations  # PEP 563 — enables X | None syntax on Python 3.9

import os
import logging
from typing import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

load_dotenv()

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
# WARN: DATABASE_URL must use the postgresql+asyncpg:// scheme.
# If the env var is missing the app will raise at import time — intentional.
DATABASE_URL: str = os.environ["DATABASE_URL"]
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
DATABASE_URL = DATABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,          # set to True locally to log all SQL statements
    pool_pre_ping=True,  # recycle stale connections automatically
    pool_size=10,
    max_overflow=20,
    prepared_statement_cache_size=0,
    connect_args={
        "statement_cache_size": 0,
    },
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # keep objects usable after commit without re-querying
    autoflush=False,
    autocommit=False,
)

# ---------------------------------------------------------------------------
# Declarative base — all ORM models must inherit from this
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass

# ---------------------------------------------------------------------------
# FastAPI dependency — inject via Depends(get_db)
# ---------------------------------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yields an AsyncSession and guarantees it is closed after the request,
    even if an exception is raised. Never create sessions outside this
    dependency; always use Depends(get_db) in route functions.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
