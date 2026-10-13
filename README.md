# ExamForge — Test Series & Learning Management Platform

ExamForge is an online examination and learning platform for competitive-exam preparation, including SSC, UPSC, Banking, Railways, NEET/JEE, and other test series.

This README distinguishes the **current checked-in implementation** from the **intended cPanel deployment target**. The application has not yet been converted to Laravel/MySQL; do not assume the MySQL migration or cPanel deployment is complete.

## Architecture and migration status

| Layer | Current repository implementation | Intended cPanel deployment |
|---|---|---|
| Frontend | React 19, Tailwind CSS, shadcn/ui, Axios | Keep the React UI and serve its production build as static files |
| API | FastAPI (Python), split across `server.py` and supporting routers | Laravel/PHP REST API; conversion is pending |
| Database | MongoDB accessed with Motor | MySQL; schema and data migration are pending |
| Authentication | JWT; email/password and Google sign-in integration | Preserve existing flows and roles during API conversion |
| Payments | Razorpay integration; demo mode when keys are not configured | Reconfigure and test using Razorpay test keys before live mode |
| API hostname | Configured through `REACT_APP_BACKEND_URL` | Planned hostname: `https://api.jssc.online`, subject to DNS, TLS, and hosting configuration |

**Important:** The current backend source imports `AsyncIOMotorClient` and uses MongoDB-specific query/update operations. Setting a MySQL connection string alone will not convert it. The current Python backend also requires a compatible Python runtime and a persistent application process; the documented shared cPanel environment may not provide these. The planned cPanel-only route is to port the API to Laravel/PHP and MySQL before production cutover.

## Features

### Students
- Browse test series, exam categories, courses, and study materials.
- Take timed exams with a server-authoritative timer, autosave, question palette, mark-for-review, negative marking, and timeout submission.
- Take exams with either free section navigation or separately timed, locked sections.
- Switch between English and Hindi question content where translations are available.
- Review scores, explanations, section-wise results, ranks, and percentiles.
- View public leaderboards and scheduled live-mock countdowns.
- See weak-topic suggestions and course progress.
- Enroll in free content, apply coupons, and purchase eligible items through Razorpay.
- Sign in with email/password or the configured Google sign-in integration.

### Admins and teachers
- Manage the question bank, including bilingual questions and bulk CSV/XLSX import with preview and batch undo.
- Create and manage test series, tests, sections, timers, courses, course sections, lessons, categories, subjects, and study materials.
- Manage users and roles; admin-only operations include user administration, orders, coupons, and payment settings.
- Configure site branding, homepage content, legal pages, announcement bars, and SMTP/password-reset settings.
- Configure Razorpay credentials and webhook settings.

Roles used by the current application include `super_admin`, `admin`, `teacher`, `student`, and `support`. Verify role enforcement during any backend port.

## Repository layout

```text
backend/
  server.py             FastAPI app, exam engine, authentication, payments, seeding
  admin_routes.py       Admin APIs
  site_routes.py        Site settings, pages, uploads, announcement APIs
  email_routes.py       SMTP settings and password-reset APIs
  perf.py               Public-response caching middleware
  requirements.txt      Python dependencies
  tests/                Backend test suites
  uploads/              Local upload directory used by the current backend
frontend/
  src/App.js             Application routes
  src/lib/api.js         Axios API client and auth-token handling
  src/pages/             Public, student, exam, and admin screens
  src/components/        Shared UI components
database_export/
  JSON collection exports and import_db.py (MongoDB-specific; destructive to target collections)
memory/PRD.md             Product requirements, implementation history, and backlog
tests/
  Additional repository tests, if present
```

## Run the current implementation locally

These instructions run the **current FastAPI + MongoDB implementation**, not the future Laravel/MySQL target.

### Requirements
- Python 3.11 or newer
- Node.js 18 or newer
- Yarn Classic (the package metadata specifies Yarn 1.22.22)
- MongoDB 6 or newer
- A separate development/test database for tests

### Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create `backend/.env` locally (do not commit it):

```dotenv
MONGO_URL=mongodb://127.0.0.1:27017
DB_NAME=examforge_dev
CORS_ORIGINS=http://localhost:3000
JWT_SECRET=replace-with-a-long-random-secret
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=168
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
RAZORPAY_WEBHOOK_SECRET=
```

Use a unique, randomly generated JWT secret outside development. Configure Google sign-in and other optional integrations according to the relevant code and provider setup.

Start the API:

```bash
cd backend
source .venv/bin/activate
uvicorn server:app --host 127.0.0.1 --port 8001 --reload
```

The API routes are prefixed with `/api`. Use `http://127.0.0.1:8001/docs` to inspect the FastAPI OpenAPI documentation while the development server is running.

### Frontend setup

Create `frontend/.env`:

```dotenv
REACT_APP_BACKEND_URL=http://127.0.0.1:8001
```

Then install and start the React app:

```bash
cd frontend
yarn install
yarn start
```

The development frontend normally runs at `http://localhost:3000`. The API client in `frontend/src/lib/api.js` builds its base URL from `REACT_APP_BACKEND_URL`; the same variable must point to the deployed API when producing a production build.

### Production frontend build

Build only after the target API URL is decided and reachable:

```bash
cd frontend
REACT_APP_BACKEND_URL=https://api.jssc.online yarn build
```

On Windows PowerShell, set the environment variable with `$env:REACT_APP_BACKEND_URL="https://api.jssc.online"` before running `yarn build`. Replace the example hostname if deployment uses another API URL. A build does not deploy the API, configure DNS, or enable HTTPS by itself.

## API areas

The current FastAPI application exposes API routes under `/api`. Main functional areas include:

- **Authentication:** registration, login, Google sign-in, current-user lookup, forgot/reset password.
- **Catalog:** categories, subjects, test series, tests, courses, lessons, study materials, and live mocks.
- **Exam engine:** start attempt, fetch attempt, autosave answers, pause/resume where allowed, section transitions, submit, result review, and ranking.
- **Student:** dashboard, attempts, orders, entitlements, weak topics, lesson progress, certificates.
- **Content management:** question CRUD/import/undo, test builder and bulk operations, series, courses, sections, lessons, materials, and generic content updates.
- **Admin/site:** users and roles, statistics, orders, coupons, payment configuration, site layout/home content, legal pages, uploads, announcements, and SMTP settings.
- **Payments:** coupon validation, order creation and verification, Razorpay webhook.

Use the route decorators in `backend/server.py`, `backend/admin_routes.py`, `backend/site_routes.py`, and `backend/email_routes.py` as the source of truth. Keep the frontend API contract compatible when porting the backend.

## Tests

Run tests only against a dedicated disposable test database. The test suites perform database writes and deletes; do not point them at production data.

```bash
cd backend
python -m pytest tests/ -v -o addopts=''
```

Confirm the required MongoDB service and test environment variables are configured before running the current backend tests. A passing test run for the current MongoDB implementation does not prove that a future MySQL/Laravel port works; ported endpoints need equivalent regression tests.

## MySQL and cPanel migration plan

The intended target is **React static frontend + Laravel/PHP API + MySQL**, suitable for cPanel capabilities that include PHP and MySQL but do not include a Python application manager.

Migration work is not complete. Use this checklist to track it:

- [ ] Inventory all API routes, request/response shapes, authorization rules, and side effects.
- [ ] Design and review normalized MySQL tables, foreign keys, unique constraints, and indexes.
- [ ] Port authentication, password reset, Google sign-in, JWT/session behavior, roles, and suspended-user handling.
- [ ] Port question bank, CSV/XLSX import, preview, batch undo, and bulk deletion.
- [ ] Port exam attempts, server-side timing, autosave/version checks, section locking, pause/resume, timeout submission, scoring, and idempotent result creation.
- [ ] Port catalogs, courses, lessons, progress, certificates, leaderboards, and weak-topic reporting.
- [ ] Port orders, entitlements, coupon validation/usage limits, Razorpay order verification, and webhook signature verification.
- [ ] Port admin, site content, uploads, SMTP settings, and password reset.
- [ ] Transform the exported records into MySQL-compatible data; validate counts and relationships before cutover.
- [ ] Add automated regression, authorization, payment, migration, concurrency, and load tests.
- [ ] Build React against the deployed API URL and verify CORS, HTTPS, upload URLs, and deep-link routing.
- [ ] Back up the current deployment and database, perform a staging cutover, validate, and document rollback steps.

Do not use `database_export/import_db.py` against production: the script is MongoDB-specific and replaces collection contents. It is not a MySQL migration tool. Create and test a separate migration process that targets an empty staging database first.

### Planned cPanel deployment

1. Create a staging MySQL database and a dedicated database user through cPanel.
2. Implement the Laravel API and migrations in a separate staging application path.
3. Configure environment variables and secrets outside version control; disable debug mode in production.
4. Configure `api.jssc.online` only after the API hosting, DNS, document root, and TLS setup are verified.
5. Build and upload the React static files only after the API contract and hostname are ready.
6. Verify health, authentication, test start/autosave/submit, results, admin access, file uploads, email, and Razorpay test-mode flows.
7. Take verified backups and perform a controlled cutover with a rollback plan.

The existing FastAPI application cannot run on ordinary PHP-only shared hosting simply by uploading its source. If the API has not been ported to PHP, keep the frontend in staging and do not announce the cPanel deployment as production-ready.

## Security and production checklist

- Keep all `.env` files, database exports containing user data, credentials, JWT secrets, and payment secrets out of version control.
- Use a strong unique JWT secret; do not use a development fallback in production.
- Change/remove all seeded demo accounts and passwords before public launch.
- Restrict CORS to the actual frontend origin; require HTTPS for the website and API.
- Keep database credentials least-privileged and do not expose database ports publicly.
- Verify role-based authorization server-side for every admin/teacher operation.
- Validate and size-limit uploads; store uploads outside executable paths where practical.
- Verify Razorpay signatures and make payment/webhook processing idempotent. Start with test keys.
- Configure database and upload backups and test restoration.
- Use rate limits and abuse protection for login, registration, password reset, uploads, and payment endpoints.
- Load-test exam start, autosave bursts, submission bursts, and result generation before large live exams.
- Do not treat a successful frontend build or a running server as proof that the full application is production-ready.

## Product requirements and progress

See [`memory/PRD.md`](memory/PRD.md) for the implementation history, iteration notes, and remaining backlog. Update that document when a migration task is implemented and tested so that the README, source code, and deployment instructions remain consistent.
