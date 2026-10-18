"""MySQL connection/bootstrap foundation for the cPanel migration.

This module is intentionally not wired into server.py yet. The API currently uses
Mongo-specific query/update semantics throughout multiple route modules; switching
the connection alone would break production behaviour. Route conversion must land
before this module becomes the application's active database backend.
"""
from __future__ import annotations

import os
from urllib.parse import quote_plus

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy import text


def build_database_url() -> str:
    """Build an async MySQL URL from cPanel environment variables.

    Preferred: DATABASE_URL=mysql+asyncmy://...
    Alternative variables: DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD.
    Never log the resulting URL because it contains credentials.
    """
    direct_url = os.getenv("DATABASE_URL", "").strip()
    if direct_url:
        if not direct_url.startswith(("mysql+asyncmy://", "mysql+aiomysql://")):
            raise RuntimeError(
                "DATABASE_URL must use mysql+asyncmy:// or mysql+aiomysql://"
            )
        return direct_url

    required = ("DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD")
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(
            "Missing MySQL configuration variables: " + ", ".join(missing)
        )

    host = os.environ["DB_HOST"].strip()
    port = os.getenv("DB_PORT", "3306").strip()
    name = quote_plus(os.environ["DB_NAME"])
    user = quote_plus(os.environ["DB_USER"])
    password = quote_plus(os.environ["DB_PASSWORD"])
    driver = os.getenv("DB_DRIVER", "asyncmy").strip().lower()
    if driver not in ("asyncmy", "aiomysql"):
        raise RuntimeError("DB_DRIVER must be asyncmy or aiomysql")
    return f"mysql+{driver}://{user}:{password}@{host}:{port}/{name}?charset=utf8mb4"


def create_mysql_engine() -> AsyncEngine:
    """Create a pooled async engine suitable for a modest cPanel plan."""
    pool_size = int(os.getenv("DB_POOL_SIZE", "5"))
    max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "2"))
    if not 1 <= pool_size <= 20 or not 0 <= max_overflow <= 10:
        raise RuntimeError("DB_POOL_SIZE must be 1..20 and DB_MAX_OVERFLOW 0..10")
    return create_async_engine(
        build_database_url(),
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_size=pool_size,
        max_overflow=max_overflow,
        connect_args={"connect_timeout": 10},
    )


async def check_mysql_connection(engine: AsyncEngine) -> dict:
    """Return a minimal, non-sensitive connection check for deployment tests."""
    async with engine.connect() as connection:
        result = await connection.execute(text("SELECT 1"))
        value = result.scalar_one()
    return {"ok": value == 1, "database": "mysql"}
