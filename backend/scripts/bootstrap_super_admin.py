"""Explicit, one-time bootstrap for the first MySQL super administrator.

Run from the backend directory after applying Alembic migrations:
    python scripts/bootstrap_super_admin.py

Required environment variables:
    BOOTSTRAP_ADMIN_NAME
    BOOTSTRAP_ADMIN_EMAIL
    BOOTSTRAP_ADMIN_PASSWORD

The command never reads or imports MongoDB users and refuses to run when a
MySQL admin/super_admin already exists. It uses a MySQL advisory lock so two
bootstrap invocations cannot both create the first administrator.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from uuid import uuid4

import bcrypt
from dotenv import load_dotenv
from pydantic import EmailStr, TypeAdapter
from sqlalchemy import func, insert, select, text

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
load_dotenv(BACKEND_DIR / ".env")

from mysql_persistence.config import load_mysql_settings
from mysql_persistence.database import create_database_runtime
from mysql_persistence.identity import utc_naive
from mysql_persistence.models import User


LOCK_NAME = "examforge:first-super-admin-bootstrap"


async def bootstrap() -> None:
    name = os.environ.get("BOOTSTRAP_ADMIN_NAME", "").strip()
    email_raw = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "").strip()
    password = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "")

    if not name or len(name) > 120:
        raise SystemExit("BOOTSTRAP_ADMIN_NAME is required and must be at most 120 characters")
    if not email_raw:
        raise SystemExit("BOOTSTRAP_ADMIN_EMAIL is required")
    if len(password) < 14 or len(password) > 128:
        raise SystemExit("BOOTSTRAP_ADMIN_PASSWORD must be between 14 and 128 characters")

    try:
        email = str(TypeAdapter(EmailStr).validate_python(email_raw)).strip().lower()
    except Exception as exc:
        raise SystemExit("BOOTSTRAP_ADMIN_EMAIL must be a valid email address") from exc

    runtime = create_database_runtime(load_mysql_settings())
    lock_acquired = False
    try:
        # Keep the same physical connection checked out for GET_LOCK and
        # RELEASE_LOCK; MySQL advisory locks are connection-scoped.
        async with runtime.engine.connect() as connection:
            acquired = await connection.scalar(
                text("SELECT GET_LOCK(:lock_name, 15)"),
                {"lock_name": LOCK_NAME},
            )
            if acquired != 1:
                await connection.commit()
                raise SystemExit("Could not acquire the administrator bootstrap lock")
            lock_acquired = True
            await connection.commit()

            try:
                async with connection.begin():
                    existing_admins = await connection.scalar(
                        select(func.count(User.id)).where(User.role.in_(("admin", "super_admin")))
                    )
                    if int(existing_admins or 0) > 0:
                        raise SystemExit(
                            "A MySQL admin already exists. Bootstrap is one-time and will not modify accounts."
                        )

                    await connection.execute(insert(User).values(
                        id=str(uuid4()),
                        name=name,
                        email=email,
                        password_hash=bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode(),
                        role="super_admin",
                        status="active",
                        auth_provider="email",
                        phone="",
                        avatar_url=None,
                        created_at=utc_naive(),
                    ))
            finally:
                if lock_acquired:
                    await connection.execute(
                        text("SELECT RELEASE_LOCK(:lock_name)"),
                        {"lock_name": LOCK_NAME},
                    )
                    await connection.commit()
        print(f"Created the initial MySQL super administrator: {email}")
    finally:
        await runtime.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(bootstrap())
    except SystemExit:
        raise
    except Exception as exc:
        print(f"Administrator bootstrap failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
