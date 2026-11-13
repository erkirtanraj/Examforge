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

## M1 implementation status (implementation complete; merged to main)

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

## M2 implementation status (implemented; final validation and review pending)

Branch: `feature/mysql-m2-identity-authz`, based on merged M1 commit `bd0629706704bb46b57e1ba629344d8d270b26c1`.

PR: [#2 — feat(mysql): migrate M2 identity and authorization to MySQL](https://github.com/erkirtanraj/Examforge/pull/2)

### Implemented

- MySQL `User` and `PasswordResetToken` schema, Alembic revision `0002_m2_identity_authz`, and async SQLAlchemy identity repository.
- Registration, password login, current-user session validation, and Google session exchange now use MySQL identities. Public registration always creates a `student`; JWT role claims are not trusted as the current role.
- Admin user list/detail/create/update/delete, role changes, status changes and password resets use MySQL. The legacy `GET /api/admin/users` response remains an array.
- Super-admin protections are enforced again under MySQL row locks, including concurrent target-role changes. Ordinary admins cannot grant, modify or delete super-admin identities.
- Password reset tokens are hashed at rest, expire, are one-time-use, rate-limited per account, and are consumed with the password update and sibling-token invalidation in one transaction. Session invalidation accounts for JWT second-level timestamp precision.
- Added an explicit password-reset token retention utility: dry-run by default, exact database-name confirmation for deletion, configurable retention, and bounded independently committed batches. It removes used tokens after `used_at` retention and unused tokens after `expires_at` retention; no automatic startup purge or scheduler is installed.
- Admin access checks, leaderboard names, admin user counts and public site student metrics read current identity data from MySQL. No MongoDB role read remains in the exam entitlement shortcut.
- Production startup no longer creates demo accounts, sample mocks, demo coupons, default legal-page copy, or automatic subject backfills. The initial MySQL super-admin is provisioned explicitly with `backend/scripts/bootstrap_super_admin.py`.
- Added a dry-run-first MongoDB identity importer. It preserves UUIDs and reset-token state, blocks conflicts, does not mutate MongoDB, and restricts `--apply` to `examforge_local`.
- MongoDB remains in use for catalog, tests, attempts, results, commerce and other operational collections that are outside M2. No dual-write was introduced.

### Security and compatibility review

- Production JWT startup requires a non-default secret of at least 32 characters.
- JWT identity claims are validated and each authenticated request re-reads current user status and role from MySQL.
- Password reset and admin identity mutations invalidate existing sessions.
- Legacy admin list and role endpoints are consolidated onto the MySQL identity repository.
- The import and bootstrap utilities are explicit operator actions; neither runs automatically at application startup.
- Existing API response shapes and role names are preserved for the migrated endpoints.

### Validation

- User-verified local run on Windows / Python 3.11 / MySQL 8.4 before the final review hardening:
  - API module compilation passed.
  - Admin identity tests: 15 passed.
  - Full `tests/mysql_migration` suite: 91 passed.
  - Real MySQL identity integration tests: 6 passed.
- GitHub Actions run #70, commit `d6f6599dbad4cabbec3ed41c589ac86066da7631`: **91 passed, 1 warning**. Alembic reached `0002_m2_identity_authz (head)`.
- Latest review added same-second session-invalidation coverage and a CI compile step for `server.py`, `admin_routes.py`, `email_routes.py` and `site_routes.py`.
- GitHub Actions run #89 on head `ce0645d955a7a68cbc6568f91edfe22bd2182ba5`: **92 passed, 1 warning**. Alembic reached `0002_m2_identity_authz (head)`; API module compilation passed.

### Remaining gates

- Run the MongoDB identity import in read-only dry-run mode against the user's actual local data, inspect the report, and obtain explicit approval before any `--apply`.
- Production migration requires a separately reviewed backup, import, cutover, smoke-test and rollback runbook. The local-only importer is not a production migration tool.
- PR #2 is open and ready for review. A self-review comment is present; obtain an independent repository-owner review before merge.
- The latest code changes and cleanup utility are on `feature/mysql-m2-identity-authz`; wait for CI to complete and review the final diff. No M2 changes are in `main`; do not merge without explicit repository-owner approval.



## Owner-directed phase sequencing update (2026-11-12)

The repository owner explicitly requested proceeding past M2 without waiting for its approval. M2 remains unmerged and is retained as the parent branch for stacked work; this does not imply M2 has passed independent review or is approved for production.

- M3 work is isolated on `feature/mysql-m3-catalog-content`, based on the current M2 feature head.
- The M3 pull request targets `feature/mysql-m2-identity-authz` rather than `main`. This keeps the M2 dependency visible and prevents unreviewed M2 commits from being merged to `main` through an M3 PR.
- M3 initial schema slice: categories, subjects, questions/options, test series/tests/sections, courses/sections/lessons, and study materials.
- M3 remains in progress until route/repository migration, import preview/undo parity, API contract tests, MySQL integration tests, and independent review are complete.
- M3 local validation of the initial schema: 109 migration tests passed; Alembic reached `0003_m3_catalog_content (head)` on the isolated local database.
- Follow-on migrations `0004_m3_question_import_batches` and `0005_m3_subject_created_at` add indexed import-batch IDs for transactional undo and preserve the subject `created_at` API field.
- Added `CatalogRepository` and moved category/subject listing and creation plus question listing/creation/bulk insert and CSV/Excel import preview/commit/undo onto MySQL. Existing response keys are serialized to the legacy API shape.
- During the transition, import undo also detaches deleted question IDs from legacy Mongo-backed test documents because M4 has not moved exam construction yet; this compatibility cleanup is temporary and must be removed once the exam engine is relational.
- Added repository serialization/import-batch unit tests. The new route/repository slice still needs local MySQL validation, API regression tests, and independent review. Test-series, exam, course, lesson and study-material handlers remain on MongoDB.
- M4–M7 will be stacked on the preceding phase branch and will not be represented as complete merely because their schema/planning work exists.
