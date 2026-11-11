# MySQL migration tests

These tests exercise the isolated SQLAlchemy foundation. They do not import or modify the existing MongoDB runtime.

## Install (from backend/)

```powershell
# Install the existing application dependencies first (includes FastAPI, httpx, pytest and pytest-xdist).
python -m pip install -r requirements.txt

# Then install the additional MySQL persistence dependencies.
python -m pip install -r requirements-mysql.txt
```

## Run the M1 unit tests

```powershell
python -m pytest -n 0 tests/mysql_migration/test_mysql_config.py tests/mysql_migration/test_mysql_session.py tests/mysql_migration/test_mysql_health.py
```

The unit tests do not open a database connection and do not require a database password.

## Configure local MySQL

Copy `.env.mysql.example` to `.env` only if that file does not already exist. Preserve the existing MongoDB `.env` values while the API migration is in progress. Add the MYSQL_* variables from the example, using the locally created `examforge_app` credentials. Never commit `.env`.

## Alembic

From `backend/`, with the local MySQL variables available in `.env`:

```powershell
alembic -c alembic.ini upgrade head
alembic -c alembic.ini current
```

The initial revision set is intentionally empty: it establishes migration infrastructure without creating guessed application tables. Application schema revisions will be added after entity relationships are reviewed in M2/M3.

## Safety

- Destructive integration fixtures must call `require_approved_test_database()`; the only accepted database name is exactly `examforge_test`.
- Never point tests at `examforge_local`, production, or MongoDB.
- Do not use SQLite as a substitute for MySQL 8.4 integration tests.
- No application routes are switched to MySQL in M1. The existing FastAPI API continues to use MongoDB until each route family has been migrated and reviewed.
