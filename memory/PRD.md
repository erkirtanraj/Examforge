# ExamForge — Test Series + LMS Platform PRD

## Original Problem
Secure cPanel-based Test Series + LMS (PRD specified Laravel 12/PHP/MySQL). User approved building on React + FastAPI + MongoDB while keeping the PRD's intended look/behavior, migrating later.

## User Choices
- MVP scope: Core LMS + Test Engine, Courses & Study Materials, Payments
- Payments: Razorpay (user to provide Key ID + Secret)
- Auth: custom email/password with roles + Emergent Google login (both)
- Design: dark exam-portal default (design agent)

## Architecture
- Backend: FastAPI single `server.py`, MongoDB (motor), JWT (bcrypt), Razorpay SDK
- Frontend: React + Tailwind + shadcn, pages in `src/pages`, auth context `src/lib/auth.jsx`

## Implemented (2026-06)
- JWT auth with roles; seeded admin/teacher/student
- Categories, subjects, question bank API (single/bulk), test series + tests API
- Exam engine: server-authoritative timer, autosave with version guard, auto-submit on timeout, idempotent scoring with negative marking, answer review
- Courses → sections → lessons, lesson completion + progress
- Study materials library
- Orders + entitlements; free items granted instantly; Razorpay order/verify/webhook (DEMO MODE until keys set)
- Student dashboard, admin dashboard (stats, users, orders)
- Tested: iteration_1 100% backend + frontend

## Iteration 2 (2026-06)
- Admin panel with sidebar (Dashboard, Question Bank, Test Series, Tests, Courses, Study Materials, Categories, Users, Orders, Settings); teachers see content sections only
- Full CRUD builders (generic /api/content/{kind}/{id} PUT/DELETE with cascades), test builder with question picker, course → section → lesson editor
- Users: role management
- Settings: Razorpay Key ID/Secret stored in DB (masked), optional webhook secret with auto-generate, test-connection; payments read settings live
- Google sign-in (Emergent Auth) issuing our JWT; users upserted by email
- All-India Rank, percentile, top-5 leaderboard (first attempt per student)
- Tested: iteration_2 28/28 backend, admin UI flows

## Iteration 3 (2026-06)
- Bulk question import (CSV/XLSX): preview, row-level errors, defaults, commit, undo by batch
- Exam sections: free-navigation tabs or per-section timers (server-enforced, only current section served, auto-advance, locked past sections); section-wise result breakdown; test builder sections editor
- Public leaderboards (/leaderboard, /leaderboard/:testId): podium, live refresh, your-rank card, tie-aware ranks, time tiebreak
- Seeded 'SSC CGL Tier I · Sectional Mock 1' and 'SBI PO Prelims · Sectional Mock 1'
- Tested: iteration_3 19/19 backend + UI flows

## Iteration 4 (2026-06)
- Scheduled All-India live mocks (live_start_at + live window; server blocks early start; home countdown banner; 'Opens in' on series page)
- Coupons: admin CRUD (percent/flat, max uses, expiry, per-series scope, active), validate endpoint, discounted Razorpay amount, 100% → free, one use per student; seeded WELCOME20
- Weak topic report on dashboard with suggested practice tests
- Bilingual (EN/हिंदी) questions: form toggle, *_hi import columns, exam + result language switch, Devanagari font; 8 seeded Hindi questions
- Tested: iteration_4 27/27 backend + UI flows

## Backlog
- P0: Admin enters real Razorpay keys in Settings (currently demo mode); atomic coupon max-use reservation for paid checkouts
- P1: live-mock registration + email reminders, Hindi UI, practice-from-mistakes quizzes, bookmarks, notifications, certificates, file uploads (object storage), light theme toggle
- P2: blog/FAQ/pricing/policy pages, split server.py into routers, Laravel 12 + MySQL migration for cPanel

## Changelog (Jun 2026)
- Packaged downloadable zips: ExamForge_Full.zip, ExamForge_Code.zip, ExamForge_Database.zip (JSON + mongodump BSON archive, restore via import_db.py or mongorestore). .env files excluded.
- Jun 2026: Admin-managed site content — Site Settings (header/footer), Home Page (hero, live/override stats, features), Legal Pages (markdown CRUD at /page/<slug>). Endpoints: GET /api/site, PUT /api/admin/site/layout|home, /api/pages/{slug}, /api/admin/pages CRUD. Tested iteration_5 (100%).
- Jun 2026: Logo & branding (upload to local /app/backend/uploads or paste URL, favicon, show-brand-name toggle) in Site Settings; POST /api/admin/uploads, static /api/uploads. Performance: lazy routes, lazy images, localStorage site cache, server 60s cache for public GETs (perf.py) cleared on admin writes, GZip. Mobile fixes (series detail, admin courses, exam top bar). Tested iteration_6 (100%).
- Jun 2026: Announcement Bar (home page only) — admin page /admin/announcement + shortcut in Site Settings; message, style, CTA, coupon copy, schedule, on/off; dismissible per version. PUT /api/admin/site/announcement. Tested iteration_7 (100%).
- Jun 2026: Brand colours (presets + custom, CSS-var themed Tailwind blue/cyan), banner click stats (POST /api/announcement/events, GET /api/admin/announcement/stats). Section-wise marks (+/−) & language (bilingual/en/hi) in tests. Users admin: create/edit/reset password/suspend/delete (admin_routes.py), suspended + tokens_valid_after enforced in get_current_user. Subjects manager + subject on questions/import/filter + subject-wise weak report. Question bank server pagination (10..5000) + bulk delete. Forgot/reset password via admin SMTP settings (/admin/email, email_routes.py). Demo creds removed from login. Self-tested via curl/screenshots (testing agent NOT run per user request).
- Jun 2026: Test builder — duplicate (1-20 copies, auto-numbered, saved as draft, live time cleared), series filter, multi-select bulk Assign to series / Duplicate / Publish / Unpublish / Delete. Endpoints POST /api/admin/tests/duplicate, /api/admin/tests/bulk. Self-tested (curl + UI).
- Jun 2026: Thumbnail upload + 16:9 preview (ImageField wide) for Test Series, Courses and Study Materials (new thumbnail field); teachers can upload; public pages resolve uploaded URLs via assetUrl. Self-tested.
- Jun 2026: Course view — custom chrome-less YouTube player (IFrame API, controls=0, cropped title/logo strip, own cover/pause/end overlays), Play/Pause, Prev/Next lesson, seek bar + time; persisted completed ticks (completed_ids in /api/my/progress), lesson numbering, "Lesson X of Y", Next marks complete, auto-complete on video end. Self-tested.
- Jun 2026: Resume playback (server lesson_positions + localStorage fallback, Resume/Start over prompt, >95% restarts), playback speed 0.5-2x remembered, course completion certificate (admin per-course toggle certificate_enabled, POST /api/courses/{id}/certificate, jsPDF download, public /verify/:code via GET /api/certificates/{code}). Tested iteration_8 (100%).
