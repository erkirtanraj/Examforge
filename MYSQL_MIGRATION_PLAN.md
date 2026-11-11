# ExamForge Full MySQL Migration Plan

## Decision and scope

- Target: MySQL 8.4 (use the already-installed local instance).
- Backend remains FastAPI; preserve the existing HTTP API contract consumed by React.
- Persistence target: SQLAlchemy 2.x with Alembic-managed schema migrations and an async MySQL driver.
- Data scope for this work: fresh local MySQL database only. Do not import MongoDB exports or connect to a production database.
- Source of truth for the migration baseline: `main` at the time this branch was created.
- No merge to `main` without explicit repository-owner approval.

## Audit findings (main)

The current backend is MongoDB-native:
- `backend/server.py`: 1,986 lines; 54 `find_one`, 45 `find`, 24 `insert_one`, 12 `insert_many`, 19 `update_one`, 4 `update_many`, 2 `delete_one`, 5 `delete_many`, 14 `count_documents`, 1 aggregation, and 5 index-creation calls.
- `backend/admin_routes.py`: 244 lines; uses Mongo query documents, regex operators, cursor operations and bulk updates/deletes.
- `backend/site_routes.py`: 325 lines; Mongo-backed settings, pages, announcement and site-content operations.
- `backend/email_routes.py`: 162 lines; Mongo-backed SMTP settings and password-reset token operations.
- Existing backend tests include live HTTP tests that use PyMongo and demo accounts. They are not yet a MySQL regression suite and must be isolated from any production data.
- React accesses the backend through `REACT_APP_BACKEND_URL`; it does not connect directly to MongoDB.

An older branch, `feature/cpanel-mysql-migration`, exists but is not a safe starting point without reconciliation: it is 56 commits ahead and 2 behind `main`, and its diff removes the checked-in `database_export/` assets. It contains an initial SQLAlchemy connection/model slice, not proof of a complete API migration. This new branch is intentionally created from `main`.

## Migration architecture

1. SQLAlchemy 2.x declarative models and async sessions; no raw credentials in source or logs.
2. Alembic for versioned schema changes. Application startup must not silently create or mutate schema.
3. Repository/service layer separates route logic from persistence. Avoid a generic Mongo-to-SQL compatibility shim.
4. Explicit relational constraints and indexes for users/roles, catalog, questions/options, tests/sections, attempts/answers/results, courses/lessons/progress, materials, coupons, orders/payments/entitlements, site settings/pages, announcements, SMTP settings and password-reset tokens.
5. Preserve externally visible JSON shapes and authorization semantics unless a separately reviewed API change is required.
6. Store flexible, low-query-frequency metadata as JSON only where justified; core relationships and query fields must be normalized.
7. Use transactions for enrollment/payment state changes, attempt submission/result creation, bulk operations and other multi-row invariants.
8. Keep MongoDB code and exports untouched until MySQL parity is demonstrated. No dual-write in this fresh-database phase.

## Implementation phases

- M0 — baseline and safety: branch, inventory, MySQL connectivity check, baseline test results, test DB isolation.
- M1 — persistence foundation: configuration validation, engine/session lifecycle, model conventions, Alembic, health checks and unit tests.
- M2 — identity and authorization: users, roles, login/register, current-user, password reset, Google-auth integration boundaries, suspended-user/session invalidation.
- M3 — catalog and content: categories, subjects, questions/options, question import/preview/undo, test series, tests/sections, courses/lessons, materials.
- M4 — exam engine: attempt creation, server-authoritative timer, autosave/version checks, pause/resume, section locking, submit, scoring, result review, rank/weak-topic queries.
- M5 — commerce: coupons, orders, Razorpay verification/webhooks, entitlements, idempotency and transaction boundaries.
- M6 — administration and site operations: admin stats/users/roles, settings, pages, home/header/footer, announcements, uploads and SMTP.
- M7 — parity, performance and cutover readiness: complete regression matrix, query/index review, concurrency/load tests, security review, local runbook and rollback notes.

Each phase must be independently testable and reviewed before proceeding to the next dependent phase.

## Test strategy and required coverage

### Test isolation
- Use a dedicated disposable database such as `examforge_test`, never the developer's existing application database.
- Tests must fail fast if the configured database name is not an approved test/local name.
- Never run destructive test setup against a non-test database.
- Use unique test records and deterministic cleanup; use transaction rollback where appropriate.
- Do not import `database_export/` or use `database_export/import_db.py` for this fresh-database scope.

### Test layers
- Unit: URL/config parsing, model constraints, password/token helpers, scoring, coupon calculations and repository methods.
- Database integration: CRUD, uniqueness, foreign keys, nullable relationships, JSON serialization, transaction rollback, pagination and concurrent updates against MySQL 8.4.
- API regression: existing request/response contracts, status codes, validation, role boundaries and error behavior.
- Feature regression: registration/login, admin/teacher/student permissions, question import, exam start/autosave/submit, results/rankings, course progress, coupon/order/payment webhook.
- Frontend contract smoke: auth token handling, catalog, exam flows and admin screens against the unchanged API contract.
- Performance/security: connection pool behavior, query plans/indexes, race/idempotency tests, rate limits, SQL injection resistance and secret redaction.

### Required acceptance gates
- All new MySQL unit and integration tests pass on MySQL 8.4.
- No route in the migrated path imports or relies on Motor/PyMongo semantics.
- Existing API regression tests pass or have documented, approved behavior changes.
- Authorization tests prove students cannot access admin/teacher operations.
- Payment and exam submission operations are transaction-safe and idempotent.
- Fresh schema can be created solely through Alembic from an empty database.
- Frontend build and critical user journeys pass.
- No secrets, local `.env` files, database dumps or real user data are committed.

## Review-before-merge policy

- Work only on `feature/mysql-full-migration` or narrowly scoped child branches.
- Keep pull requests small and phase-scoped; attach schema diff, test commands/results, API compatibility notes and rollback considerations.
- Review migrations for destructive DDL, data loss, missing indexes, locking and downgrade behavior.
- Review all auth, payment, exam scoring and authorization changes with extra scrutiny.
- Do not merge automatically. The repository owner must explicitly approve the final review and merge.
- Keep `main` unchanged until that approval is given.

## M1 implementation status (in progress)

Implemented on `feature/mysql-full-migration`:
- Validated `mysql+asyncmy` configuration from `DATABASE_URL` or `MYSQL_*` variables, including URL-safe credential handling and redacted URL output.
- Async SQLAlchemy engine/session runtime with connection pre-ping, bounded pool settings, health ping and disposal.
- Declarative SQLAlchemy base with deterministic constraint naming conventions.
- Opt-in `/health/mysql` router; it is deliberately not mounted into the existing Mongo-backed app yet.
- Async Alembic environment and revision template. The initial migration history is empty by design; no application schema has been guessed or applied.
- Unit tests for config, database-name safety, engine construction and health response/error redaction.
- Separate `requirements-mysql.txt` and `.env.mysql.example`; existing Motor/PyMongo dependencies and runtime remain untouched.

Remaining M1 validation:
1. Install the additional requirements in the local backend virtual environment.
2. Run the M1 tests from `backend/` using the documented `-n 0` command.
3. Run Alembic `upgrade head` and `current` against the local `examforge_local` database (empty baseline only).
4. Review the resulting commit diff and resolve any test or migration-tool issues before M1 is marked complete.

No production database, MongoDB export, or existing Mongo-backed API route is touched by M1. Do not merge to `main` without explicit approval.
