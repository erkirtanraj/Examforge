#!/usr/bin/env python3
"""Explicitly create the normalized first-slice MySQL schema.

This is opt-in: it is never run automatically by the web application. It creates
missing tables only and does not alter or delete existing tables/data.
"""
from __future__ import annotations

import asyncio
import os

from sqlalchemy.ext.asyncio import create_async_engine

from mysql_config import build_database_url
from mysql_models import Base


async def main() -> None:
    if os.getenv("ALLOW_SCHEMA_CREATE") != "YES":
        raise SystemExit(
            "Schema creation is disabled by default. Review the models and set "
            "ALLOW_SCHEMA_CREATE=YES to create missing tables."
        )
    url = build_database_url()
    engine = create_async_engine(url, pool_pre_ping=True, pool_recycle=1800)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("Schema creation complete. Existing tables were not altered or deleted.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
