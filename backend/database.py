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
from sqlalchemy.pool import NullPool

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

# When using Supabase (PgBouncer in transaction mode):
#   1. NullPool — disable SQLAlchemy connection pooling; PgBouncer does it.
#   2. statement_cache_size=0 — disable asyncpg prepared statement cache
#      because PgBouncer transaction mode does NOT support prepared statements.
# These two settings together prevent the "prepared statement does not exist"
# and connection-hang errors we were hitting in production.
engine = create_async_engine(
    DATABASE_URL,
    echo=False,          # set to True locally to log all SQL statements
    poolclass=NullPool,  # let PgBouncer handle connection pooling
    connect_args={
        "statement_cache_size": 0,          # disable asyncpg statement cache
        "prepared_statement_cache_size": 0,  # disable asyncpg prepared stmt cache
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
