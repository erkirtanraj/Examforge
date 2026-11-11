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

## M1 implementation status (implementation complete; PR review pending)

Implemented on `feature/mysql-full-migration`:
- Validated `mysql+asyncmy` configuration from `DATABASE_URL` or `MYSQL_*` variables, including URL-safe credential handling and redacted URL output.
- Async SQLAlchemy engine/session runtime with connection pre-ping, bounded pool settings, health ping and disposal.
- Declarative SQLAlchemy base with deterministic constraint naming conventions.
- Opt-in `/health/mysql` router; it is deliberately not mounted into the existing Mongo-backed app yet.
- Async Alembic environment and revision template. The initial migration history is empty by design; no application schema has been guessed or applied.
- Unit tests for config, database-name safety, engine construction and health response/error redaction.
- Separate `requirements-mysql.txt` and `.env.mysql.example`; existing Motor/PyMongo dependencies and runtime remain untouched.

### M1 validation completed locally

- Installed the isolated M1 test dependencies and `requirements-mysql.txt`.
- `python -m pytest -n 0 tests/mysql_migration` — 10 passed.
- Applied the empty baseline to the local `examforge_local` database; `alembic_version` records `0001_m1_baseline`.
- `python -m alembic -c alembic.ini current` — `0001_m1_baseline (head)`.
- `git status --short` — clean.
- `git diff main...feature/mysql-full-migration --check` — no whitespace errors.
- Local `backend/.env` is ignored by Git and is not part of the PR.

### Review and merge status

- PR #1 was reviewed and squash-merged to `main` on 2026-11-11.
- Merge commit: `bd0629706704bb46b57e1ba629344d8d270b26c1`.
- Added `.github/workflows/mysql-m1-tests.yml` for isolated M1 tests. No workflow run or commit status was visible immediately after merge; confirm the first run in GitHub Actions.
- No production database, MongoDB export, or existing Mongo-backed API route was touched by M1.

## M2 implementation status (in progress on feature branch)

Branch: `feature/mysql-m2-identity-authz`, created from the merged M1 `main` commit.

### Identity and authorization contract audit

Existing API contracts to preserve:
- `POST /api/auth/register` returns `{token, user}`; frontend stores the bearer token in localStorage key `lms_token`.
- `POST /api/auth/login` returns `{token, user}`.
- `GET /api/auth/me` returns the authenticated user object.
- `POST /api/auth/google` accepts `{session_id}` and exchanges the trusted OAuth session with the existing identity service.
- Password reset routes: `POST /api/auth/forgot-password`, `GET /api/auth/reset-password/{token}`, and `POST /api/auth/reset-password`.
- Existing role names: `super_admin`, `admin`, `teacher`, `student`, `support`.
- Existing account states: `active`, `suspended`. Google-only accounts may have no password hash.
- Existing API user IDs are UUID strings; preserve these IDs and response shapes.

Security findings to address during M2 route migration:
1. **Addressed in the current M2 branch:** public registration no longer accepts a role field and always creates a `student`. Elevated roles remain staff-managed.
2. **Addressed in the current M2 branch:** production (`APP_ENV`, `ENVIRONMENT`, or `NODE_ENV` set to `production`/`prod`) now fails startup unless `JWT_SECRET` is at least 32 characters and is not the development fallback. Non-production keeps the local fallback for compatibility.
3. **Addressed in the current M2 branch:** the main `/api/admin/users/{user_id}/role` handler and the separate admin user-management routes both protect existing `super_admin` targets from ordinary admins and prevent ordinary admins from granting that role.
4. **Partially addressed in the current M2 branch:** JWT validation rejects missing/malformed `uid` and `iat` claims as 401 and validates the session invalidation timestamp. It still reads the current identity from Mongo until the coordinated MySQL route cutover; current role/status re-read must move with that cutover.
5. Password-reset token consumption, password update, and invalidation of other reset tokens must be one database transaction; preserve one-time use, expiry, and generic forgot-password responses.
6. **Partially addressed in the current M2 branch:** the startup path no longer invokes the predictable demo-user seed routine in production. Review other sample-data seed routines and replace the development seed workflow with an explicit operator-provisioned initial super-admin before production cutover.
7. Existing auth routes and admin user endpoints currently read/write MongoDB; they must switch together to the MySQL user repository so authorization cannot observe inconsistent identity stores. Do not dual-write.

### MongoDB identity import utility (preflight stage)

Added `backend/scripts/migrate_mongo_identities.py` and focused normalization/preflight tests.

Safety properties:
- Default invocation is read-only dry-run; `--dry-run` is explicit but optional.
- `--apply` is restricted to the exact MySQL database name `examforge_local`; this utility cannot write to a production-named database.
- Reads MongoDB `users` and `password_reset_tokens`; it never updates or deletes MongoDB records.
- Preserves UUIDs, normalized email, password hashes, role/status/provider, profile fields, UTC timestamps, session invalidation metadata, user references, and reset-token use/expiry state.
- Detects malformed records, case-insensitive duplicate source emails, missing user references, duplicate token hashes, and target identity/token mismatches. Any conflict blocks the entire import.
- Uses a single MySQL transaction for new records and a two-pass insert for self-referencing user foreign keys.
- Idempotent re-runs accept only exact existing-record parity; mismatched existing records are reported as conflicts, never overwritten.
- Output excludes password hashes, reset-token hashes, and connection credentials.

Important:
- The utility has been committed to the M2 feature branch but has not yet been run against the user's local MongoDB/MySQL data.
- Do not run `--apply` until the dry-run report is reviewed and explicitly approved. Production migration requires a separately reviewed process and cutover plan.
- The migration does not switch any authentication or admin API route and does not perform dual writes.

### M2 schema work started

Implemented on `feature/mysql-m2-identity-authz`:
- SQLAlchemy `User` model with string UUID primary key, unique email, password hash nullable for Google accounts, role/status/auth-provider constraints, profile fields, and session invalidation timestamp.
- SQLAlchemy `PasswordResetToken` model with unique token hash, user foreign key/cascade, one-time-use fields, expiry, and query indexes.
- Alembic revision `0002_m2_identity_authz` creates the two tables after the M1 baseline.
- Metadata tests cover identity columns, role/status/provider constraints, unique email/token hashes, and token ownership cascade.
- Added a framework-independent `IdentityRepository` for MySQL user lookup/create/update/delete, hashed reset-token creation, and transactional reset-token consumption/password update/sibling-token invalidation.
- Repository normalizes UTC timestamps, preserves legacy user dictionary fields, omits password hashes for public serialization, and translates duplicate-email conflicts.
- Added repository serialization/time-normalization unit tests.
- Added production JWT-secret policy and malformed identity-claim validation helpers with unit tests.
- Updated auth handling to reject malformed JWT identity claims, validate session invalidation metadata, force public registration to `student`, and skip predictable demo-account seeding in production.
- Protected existing `super_admin` targets in the main role-change endpoint as well as the admin user-management routes; added policy tests.
- CI path filters now run the migration/auth test job when these auth files change.

M2 schema/repository/auth-security validation completed locally on 2026-11-11:
- `python -m compileall -q server.py auth_security.py admin_routes.py email_routes.py` — passed.
- `python -m pytest -n 0 tests/mysql_migration` — 40 passed (one non-blocking Starlette/AnyIO deprecation warning).
- `git diff --check` — passed; `git status --short` — clean.
- Local Alembic current/heads previously verified at `0002_m2_identity_authz (head)`; rerun after any schema changes.
- `alembic current` and `alembic heads` — `0002_m2_identity_authz (head)`.
- `git status --short` — clean before the repository-layer commits.

Not yet complete:
- Auth and admin user routes are not switched to MySQL.
- Coordinated MySQL auth/admin route cutover, Google identity boundary, and API-level transactional password reset remain to implement.
- Repository database integration/concurrency tests and full auth/API regression tests remain to implement.
- Do not merge M2 until schema, route, API regression, authorization, and MySQL integration tests pass and the PR is reviewed.

No M2 change is merged to `main`.
