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

## Backlog
- P0: Razorpay live keys; admin UIs for question bank / test builder / course builder (APIs exist); Emergent Google login
- P1: sections in tests (Quant/Reasoning), bookmarks, notifications, certificates, file uploads (object storage), light theme toggle
- P2: blog/FAQ/pricing pages, coupons, leaderboard/ranking, bulk CSV import, Laravel migration docs
