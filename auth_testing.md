# Auth Testing Notes (ExamForge)

This app uses its OWN JWT (Bearer token in localStorage key `lms_token`) for both email/password and Google login.
Google flow: Login page "Continue with Google" -> https://auth.emergentagent.com/?redirect=<origin>/dashboard -> returns to
`/dashboard#session_id=...` -> frontend POSTs `/api/auth/google {session_id}` -> backend calls Emergent session-data,
upserts user by email (default role student), returns `{token, user}`.

## Testing without real Google
- Real Google OAuth cannot be automated; verify the button redirects to auth.emergentagent.com with a `redirect` param equal to `<origin>/dashboard`.
- `/api/auth/google` with an invalid session_id must return 401.
- To test auth-gated pages, login via `/api/auth/login` (see /app/memory/test_credentials.md) and set localStorage `lms_token`.

## Checklist
- Users collection uses custom `id` (uuid) field; all queries exclude `_id`.
- Google users have no password_hash; email/password login for them must return 401 (not 500).
