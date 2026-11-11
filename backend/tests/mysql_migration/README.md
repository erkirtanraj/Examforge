# MySQL migration test plan

This directory is reserved for tests introduced with the MySQL persistence foundation.

## Rules
- Use only a dedicated disposable database (for example `examforge_test`).
- Refuse to run destructive setup when the database name is not explicitly approved as local/test.
- Never read or write production credentials or production data.
- Do not import MongoDB exports for the fresh-database migration.
- Integration tests must target MySQL 8.4; SQLite is not an adequate substitute for MySQL-specific behavior, constraints, JSON, collation or transaction semantics.

## Planned suites
- `test_mysql_config.py`: URL construction, invalid schemes, missing variables, credential URL encoding, pool bounds and secret redaction.
- `test_mysql_session.py`: engine lifecycle, connection health and session rollback/commit behavior.
- `test_mysql_models.py`: primary/foreign keys, uniqueness, nullability, indexes and JSON payload handling.
- `test_mysql_repositories.py`: repository CRUD, pagination, filtering and transaction boundaries.
- `test_mysql_api_auth.py`: auth contract, token expiry/revocation and role isolation.
- `test_mysql_exam_flows.py`: attempt start, autosave concurrency, section locking, submit idempotency and scoring parity.
- `test_mysql_payments.py`: coupon limits, order verification, webhook signature validation and idempotency.

Tests will be added with the corresponding implementation phase; this initial audit commit intentionally adds no unexecutable placeholder tests.
