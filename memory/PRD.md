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

## Backlog
- P0: Admin enters real Razorpay keys in Settings (currently demo mode)
- P1: sections in tests (Quant/Reasoning), bookmarks, notifications, certificates, file uploads (object storage), light theme toggle
- P2: blog/FAQ/pricing pages, coupons, leaderboard/ranking, bulk CSV import, Laravel migration docs
