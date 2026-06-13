# backend/alembic/env.py

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# ---------------------------------------------------------------------------
# Make sure 'backend/' is on sys.path so our local imports resolve.
# Alembic is run from the backend/ directory, so the parent of alembic/ is
# already on sys.path via prepend_sys_path=. in alembic.ini.
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent          # .../backend/
sys.path.insert(0, str(BASE_DIR.parent))                   # .../project root/

# Load .env so DATABASE_URL is available
load_dotenv(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Import Base + all models so Alembic can see the full metadata for
# autogenerate. Models must be imported before target_metadata is set.
# ---------------------------------------------------------------------------
from backend.database import Base                          # noqa: E402
from backend.models.application import (                   # noqa: F401, E402
    Application,
    TimelineEvent,
    NotificationSettings,
)

# ---------------------------------------------------------------------------
# Alembic config object — gives access to values in alembic.ini
# ---------------------------------------------------------------------------
config = context.config

# Inject DATABASE_URL from environment (overrides any value in alembic.ini)
DATABASE_URL: str = os.environ["DATABASE_URL"]
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
DATABASE_URL = DATABASE_URL.replace("?pgbouncer=true", "").replace("&pgbouncer=true", "")

if "?" in DATABASE_URL:
    DATABASE_URL += "&prepared_statement_cache_size=0"
else:
    DATABASE_URL += "?prepared_statement_cache_size=0"

# Escape % signs so ConfigParser doesn't treat them as interpolation characters
escaped_url = DATABASE_URL.replace("%", "%%")
config.set_main_option("sqlalchemy.url", escaped_url)

# Set up Python logging from alembic.ini [loggers] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# This is the MetaData object used by autogenerate support
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline migration (no live DB connection) — generates SQL script
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    In this scenario we don't actually need a real database connection; instead
    we render the SQL to stdout/a file so it can be applied manually.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migration (async, connects to the real DB)
# ---------------------------------------------------------------------------
def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run the migrations through a sync wrapper."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
