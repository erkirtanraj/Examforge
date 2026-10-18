#!/usr/bin/env python3
"""Safe preflight checks for Examforge's cPanel Python application.

Prints only presence/validity flags, never environment variable values or credentials.
This script does not migrate data, modify the schema, or switch the running API to MySQL.
"""
from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
from urllib.parse import urlsplit


def present(name: str) -> bool:
    return bool(os.getenv(name, "").strip())


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    app_env = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "production")).strip().lower()
    if app_env == "prod":
        app_env = "production"
    checks.append(("APP_ENV", app_env in ("production", "development", "test"),
                   "valid environment label" if app_env in ("production", "development", "test") else "must be production, development, or test"))

    jwt = os.getenv("JWT_SECRET", "")
    jwt_ok = len(jwt.encode("utf-8")) >= 32 and jwt not in ("dev-secret", "changeme", "secret")
    checks.append(("JWT_SECRET", jwt_ok if app_env == "production" else bool(jwt),
                   "acceptable length for production" if jwt_ok else ("set a non-empty development secret" if app_env != "production" and jwt else "production requires a unique secret of at least 32 bytes")))

    for key in ("MONGO_URL", "DB_NAME"):
        checks.append((key, present(key), "configured" if present(key) else "missing (required by the current Mongo-backed server.py)"))

    for key in ("RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET", "RAZORPAY_WEBHOOK_SECRET"):
        # Payments may be optional; report only whether each variable is present.
        checks.append((key, True, "configured" if present(key) else "not set (optional if payments are disabled)"))

    origins = os.getenv("CORS_ORIGINS", "")
    cors = [v.strip() for v in origins.split(",") if v.strip()]
    cors_ok = bool(cors) and all(v.startswith("https://") for v in cors) if app_env == "production" else True
    checks.append(("CORS_ORIGINS", cors_ok, "production origins configured with HTTPS" if cors_ok else "set comma-separated HTTPS origins for production"))

    db_url = os.getenv("DATABASE_URL", "")
    if db_url:
        try:
            parsed = urlsplit(db_url)
            mysql_ok = parsed.scheme in ("mysql+asyncmy", "mysql+aiomysql") and bool(parsed.hostname and parsed.path.strip("/"))
        except ValueError:
            mysql_ok = False
        checks.append(("DATABASE_URL", mysql_ok, "MySQL async URL shape valid" if mysql_ok else "expected mysql+asyncmy:// or mysql+aiomysql:// URL"))
    else:
        checks.append(("DATABASE_URL", True, "not set; MySQL migration connection test skipped"))

    for module in ("fastapi", "motor", "sqlalchemy", "asyncmy", "aiomysql", "passenger_wsgi"):
        if module == "passenger_wsgi":
            # The WSGI entrypoint is a file in the current working directory, not a pip dependency.
            ok = os.path.isfile(os.path.join(os.getcwd(), "passenger_wsgi.py"))
        else:
            ok = importlib.util.find_spec(module) is not None
        checks.append((f"module:{module}", ok, "available" if ok else "not importable in this Python environment"))

    failed = False
    for name, ok, note in checks:
        print(f'{"PASS" if ok else "FAIL"}  {name}: {note}')
        if not ok:
            failed = True

    if db_url and any(name == "DATABASE_URL" and ok for name, ok, _ in checks):
        if importlib.util.find_spec("sqlalchemy") is not None:
            try:
                from sqlalchemy.ext.asyncio import create_async_engine
                async def ping():
                    engine = create_async_engine(db_url, pool_pre_ping=True, connect_args={"connect_timeout": 5})
                    try:
                        from sqlalchemy import text
                        async with engine.connect() as conn:
                            return (await conn.execute(text("SELECT 1"))).scalar_one() == 1
                    finally:
                        await engine.dispose()
                try:
                    ok = asyncio.run(ping())
                    print(f'{"PASS" if ok else "FAIL"}  mysql-connectivity: SELECT 1 {"succeeded" if ok else "returned unexpected result"}')
                    failed = failed or not ok
                except Exception as exc:
                    # Exception text can include host/database details; do not print it.
                    print("FAIL  mysql-connectivity: connection failed; inspect cPanel logs privately")
                    failed = True
            except Exception:
                print("FAIL  mysql-connectivity: SQLAlchemy driver could not be initialized")
                failed = True

    print("\nNote: the current backend/server.py still requires MongoDB. A successful MySQL ping does not mean the API has been migrated.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
