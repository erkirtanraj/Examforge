# cPanel MySQL migration status

## Target

- Frontend: React app built into `frontend/build`, served from the main domain.
- API: FastAPI under the cPanel Python application rooted at `/home/jsscexam/examforge-api`.
- Database: cPanel MySQL/MariaDB.
- API origin: `https://api.jsscexam.com`.

## Safety status

This branch is a staged migration. The existing API is MongoDB-backed and uses Mongo-specific filters, update operators, aggregation, and cursor behaviour across `server.py`, `admin_routes.py`, `site_routes.py`, and `email_routes.py`. Do not deploy it as a MySQL application yet. Replacing only the database connection would cause runtime failures and could corrupt exam, attempt, or payment workflows.

The initial MySQL connection helper is in `backend/mysql_config.py`. It is not imported by the live application until the route/data-access conversion is complete.

## Environment variables

Set these in the cPanel Python App environment configuration (never commit credentials):

- `DB_HOST`: MySQL hostname shown by cPanel
- `DB_PORT`: normally `3306`
- `DB_NAME`: full cPanel-prefixed database name
- `DB_USER`: full cPanel-prefixed database username
- `DB_PASSWORD`: database password
- `DB_DRIVER`: `asyncmy` (default) or `aiomysql`
- `JWT_SECRET`: unique random secret, at least 32 UTF-8 bytes
- `APP_ENV`: `production`
- `CORS_ORIGINS`: exact trusted frontend origin(s), e.g. `https://jsscexam.com,https://www.jsscexam.com`
- payment/email provider secrets only if those features are enabled

Do not put secrets in GitHub, frontend variables, screenshots, or chat messages.

## Required next migration stages

1. Inventory every collection operation, aggregation, update operator, index, and transaction-sensitive flow.
2. Define relational tables and JSON columns where a field is genuinely flexible; preserve public IDs and API response shapes.
3. Convert data access module-by-module, including atomic attempt submission/scoring, entitlement/payment updates, password reset tokens, and admin bulk operations.
4. Build a resumable, dry-run-first importer with counts and checksums. Keep the source database untouched until validation passes.
5. Add automated tests for auth, question bank, test start/autosave/submit/scoring, course progress, payments/webhooks, password reset, and admin actions.
6. Confirm FastAPI ASGI support on the actual cPanel Passenger stack and resolve WordPress redirects for `api.jsscexam.com`.
7. Deploy only after tests pass and a verified backup/rollback plan exists.

## Local connection smoke test

After installing the SQLAlchemy/driver dependencies and setting environment variables, run from the backend directory:

```bash
python -c 'import asyncio; from mysql_config import create_mysql_engine, check_mysql_connection; e=create_mysql_engine(); print(asyncio.run(check_mysql_connection(e))); asyncio.run(e.dispose())'
```

This checks connectivity only; it does not create or migrate application tables.
