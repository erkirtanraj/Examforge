# ExamForge — Test Series + LMS Platform

Online test series, exam engine and learning platform for competitive exams (SSC, UPSC, Banking, Railways, NEET/JEE).

**Stack:** React 19 + Tailwind + shadcn/ui (frontend) · FastAPI (Python) (backend) · MongoDB (database) · Razorpay (payments) · Emergent Google Auth + JWT (sign-in)

---

## Features

**Students**
- Test series & course catalogs with exam-category filters, study materials library
- Exam engine: server-side timer, autosave every 15s, question palette, mark for review, negative marking, auto-submit
- Exam sections — free navigation (SSC style) or separate timer per section (SBI PO style, locked once finished)
- EN / हिंदी language switch during the exam and on results
- Results with answer review, explanations, section-wise breakdown, All-India rank & percentile
- Public leaderboards with podium and live refresh
- Scheduled All-India live mocks with a home-page countdown
- Weak-topic report with suggested practice tests
- Coupons at checkout, Razorpay payments, free enrollments
- Sign in with email/password or Google

**Admins & teachers** (`/admin`, sidebar menu)
- Question bank (MCQ single/multi, True/False, numerical, Hindi versions) + bulk CSV/Excel import with preview & undo
- Test builder (sections, per-section timers, live start time), test series, courses → sections → lessons, study materials, categories
- Users & roles, orders, coupons (admin only)
- Settings → Razorpay keys, auto-generated webhook secret, connection test (admin only)

Roles: `super_admin`, `admin`, `teacher`, `student`, `support`. Teachers see content sections only.

---

## Project structure

```
backend/
  server.py            FastAPI app — all /api routes, exam engine, payments, seed data
  requirements.txt
  .env                 MONGO_URL, DB_NAME, JWT_SECRET, ... (not committed)
  tests/               pytest suites
frontend/
  src/App.js           routes
  src/lib/             api client (axios) + auth context
  src/pages/           public & student pages
  src/pages/exam/      exam engine UI (timer, sections, palette, dialogs)
  src/pages/admin/     admin panel pages
  src/components/      shared components (admin kit, banners, coupon box, rank card ...)
database_export/       JSON export of every collection + import_db.py
memory/PRD.md          product requirements & progress log
```

---

## Running locally

### Requirements
Python 3.11+, Node 18+ with Yarn, MongoDB 6+

### Backend
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```
Create `backend/.env`:
```
MONGO_URL="mongodb://localhost:27017"
DB_NAME="examforge"
CORS_ORIGINS="http://localhost:3000"
JWT_SECRET="replace-with-a-long-random-string"
JWT_ALGORITHM="HS256"
JWT_EXPIRE_HOURS=168
RAZORPAY_KEY_ID=""
RAZORPAY_KEY_SECRET=""
RAZORPAY_WEBHOOK_SECRET=""
```
```bash
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```
On first start, an empty database is filled with sample data automatically (demo accounts, categories, test series, sectional & live mocks, courses, the WELCOME20 coupon).

> `requirements.txt` includes `emergentintegrations`, which is only on Emergent's package index. If it fails to install locally, remove that line; the app doesn't import it.

### Frontend
Create `frontend/.env`:
```
REACT_APP_BACKEND_URL=http://localhost:8001
```
```bash
cd frontend
yarn install
yarn start        # http://localhost:3000
```

### Restore the exported database (optional)
```bash
cd database_export
MONGO_URL="mongodb://localhost:27017" DB_NAME="examforge" python import_db.py
```
This replaces the contents of each collection. Payment settings are not exported — re-enter Razorpay keys in Admin → Settings.

---

## Demo accounts

| Role    | Email            | Password    |
|---------|------------------|-------------|
| Admin   | admin@lms.com    | admin123    |
| Teacher | teacher@lms.com  | teacher123  |
| Student | student@lms.com  | student123  |

**Change these passwords before going live.**

---

## Payments (Razorpay)

Until keys are set, paid checkout runs in **demo mode** (free items and 100% coupons still work).

1. Razorpay Dashboard → Account & Settings → API Keys → copy Key ID and Key Secret (use `rzp_test_` keys first).
2. Admin → Settings → paste the keys → **Save settings** → **Test connection**.
3. Optional webhook: click **Generate** for a webhook secret, then in Razorpay → Webhooks add
   `<your-backend-url>/api/webhooks/razorpay` with the `payment.captured` event and the same secret.

---

## Bulk question import

Admin → Question Bank → **Import CSV / Excel** (download the template there).

| Column | Notes |
|---|---|
| `question` | required |
| `type` | `mcq`, `multi`, `true_false`, `numerical` (blank = auto-detect) |
| `option_a` … `option_h` | fill in order, at least 2 for MCQ |
| `correct` | letter (`B`), several (`A,C`), option text, `True`/`False`, or a number |
| `explanation`, `category` (name or slug), `difficulty` (easy/medium/hard), `positive_marks`, `negative_marks`, `image_url` | optional |
| `question_hi`, `option_a_hi` …, `explanation_hi` | optional Hindi versions |

Up to 2,000 rows / 5 MB per file. Rows with errors are skipped and listed by row number.

---

## Main API routes (all prefixed with `/api`)

| Area | Routes |
|---|---|
| Auth | `POST /auth/register`, `POST /auth/login`, `POST /auth/google`, `GET /auth/me` |
| Catalog | `GET /categories`, `GET /test-series`, `GET /test-series/{id}`, `GET /courses`, `GET /courses/{id}`, `GET /study-materials`, `GET /live-mocks` |
| Exam | `POST /tests/{id}/start`, `GET /attempts/{id}`, `POST /attempts/{id}/autosave`, `POST /attempts/{id}/next-section`, `POST /attempts/{id}/submit`, `GET /attempts/{id}/result` |
| Rankings | `GET /leaderboards`, `GET /tests/{id}/leaderboard` |
| Student | `GET /my/dashboard`, `GET /my/attempts`, `GET /my/orders`, `GET /my/entitlements`, `GET /my/weak-topics`, `GET /my/progress/{courseId}` |
| Payments | `POST /coupons/validate`, `POST /orders`, `POST /orders/verify`, `POST /webhooks/razorpay` |
| Content (admin/teacher) | `POST /questions`, `POST /questions/import`, `DELETE /questions/import/{batch}`, `POST /tests`, `POST /test-series`, `POST /courses`, `POST /sections`, `POST /lessons`, `POST /study-materials`, `PUT/DELETE /content/{kind}/{id}` |
| Admin | `GET /admin/stats`, `GET /admin/users`, `PUT /admin/users/{id}/role`, `GET /admin/orders`, `GET/POST/PUT/DELETE /admin/coupons`, `GET/PUT /admin/settings/payment`, `POST /admin/settings/payment/webhook-secret`, `POST /admin/settings/payment/test` |

---

## Tests
```bash
cd backend
python -m pytest tests/ -v -o addopts=''
```

---

## Production checklist
- New strong `JWT_SECRET`; restrict `CORS_ORIGINS` to your domain
- Change or remove the demo accounts
- Add live Razorpay keys and the webhook in Admin → Settings
- Keep the GitHub repo private if `database_export/users.json` is included
- Note: the original PRD targeted Laravel 12 + MySQL on cPanel; this build uses React + FastAPI + MongoDB and would need porting for cPanel shared hosting

See `PRD.md` (or `memory/PRD.md` in the repo) for the full requirements and change log.
