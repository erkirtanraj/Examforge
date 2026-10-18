# MongoDB access inventory for the MySQL migration

Source inspected on branch `feature/cpanel-mysql-migration`. This is an implementation checklist, not evidence that the API has been converted.

## Current access footprint

| Module | Approx. lines | Mongo operations counted |
|---|---:|---:|
| `backend/server.py` | 2,155 | 193 |
| `backend/admin_routes.py` | 244 | 20 |
| `backend/site_routes.py` | 342 | 20 |
| `backend/email_routes.py` | 200 | 11 |

These counts are a static scan of common `db.collection.operation` call patterns. They can undercount calls split across lines or indirect helpers.

## Collections seen in source

`users`, `password_reset_tokens`, `categories`, `subjects`, `questions`, `test_series`, `tests`, `test_attempts`, `test_results`, `courses`, `course_sections`, `lessons`, `lesson_progress`, `lesson_positions`, `certificates`, `study_materials`, `orders`, `entitlements`, `coupons`, `settings`, `pages`, `announcement_stats`.

## MongoDB semantics that must be preserved

- Reads: `find_one`, `find`, projections, sorting, limits, `count_documents`, `distinct`.
- Writes: `insert_one`, `insert_many`, `update_one`, `update_many`, `delete_one`, `delete_many`, `find_one_and_update`, upsert behaviour.
- Operators seen: `$set`, `$setOnInsert`, `$inc`, `$addToSet`, `$max`, `$pull`, `$in`, `$ne`, `$or`, `$gt`, `$exists`, `$regex`, `$options`, plus aggregation `$group`/pipeline behaviour.
- Nested arrays appear in test sections and question IDs; these need explicit relational child tables or carefully validated JSON operations.
- Password-reset token consumption, test attempt submission/scoring, payment/webhook entitlement changes, and autosave/version increments require transaction-safe/atomic SQL implementations.

## Recommended relational design

Use normalized tables for frequently filtered/updated entities: users, categories, subjects, questions, test_series, tests, test_sections, test_section_questions, test_attempts, attempt_answers, test_results, courses, course_sections, lessons, lesson_progress, lesson_positions, certificates, study_materials, orders, entitlements, coupons, password_reset_tokens, pages, settings, and announcement_stats.

Preserve current public IDs as strings during migration. Use JSON columns only for truly flexible payloads or audit snapshots—not as a blanket substitute for queryable relational columns. Add foreign keys after data-cleaning checks; do not add them blindly to a legacy dataset with unknown orphan records.

## Required acceptance tests before cutover

1. Signup/login, password reset token rate limiting, expiry, one-time consumption, and password update.
2. Category/subject/question CRUD, import batches, bulk delete, search filters, pagination, and admin permissions.
3. Test start, duplicate in-progress attempt handling, autosave/version conflict, pause/resume, expiry, final submission, score calculation, negative marks, and answer secrecy.
4. Course access, lesson progress/position, certificates, paid/free entitlements, coupons, and order lifecycle.
5. Razorpay signature/webhook verification and idempotency; no client-side payment status may grant access.
6. Site pages/settings, announcements, email SMTP settings, uploads, CORS, and public API response compatibility.
7. Load tests and rollback rehearsal against a staging database.

## Current status

- Added MySQL connection helper and initial schema.
- Added a staging importer that copies Mongo documents into `ef_documents` without changing the source.
- **Live API conversion is not complete.** The current `server.py` still imports Motor and initializes `AsyncIOMotorClient`. Do not set production traffic to this branch yet.
