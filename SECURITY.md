# ExamForge Security and Production Setup

## Required production environment

The API now fails closed when production security configuration is missing. Configure these values in the server's environment/secret manager before starting the API:

- `APP_ENV=production`
- `JWT_SECRET`: a unique random secret of at least 32 bytes. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(48))"` and store it outside Git.
- `CORS_ORIGINS`: comma-separated, exact origins for the trusted frontend, for example `https://app.example.com`. Do not use `*`.
- `MONGO_URL` and `DB_NAME`.

Production API docs/OpenAPI endpoints are disabled. Local development can set `APP_ENV=development`, which enables local CORS origins and the existing development sample-data seed. Never use that setting in production.

## First administrator and password rotation

For a new production database, run from the repository root after setting `MONGO_URL` and `DB_NAME` (and placing environment variables in `backend/.env` if desired):

```bash
python backend/create_admin.py --email admin@example.com --name "ExamForge Administrator"
```

The script prompts for a password, creates only the first super administrator, and never prints the password. To rotate an existing admin/super-admin password and invalidate existing sessions:

```bash
python backend/create_admin.py --email admin@example.com --reset-existing
```

The script refuses to create another first administrator if one already exists. Public registration always creates student accounts.

If the database was previously started with an older version of ExamForge, immediately rotate or remove the old demo accounts (including any account created from the old sample seed) before exposing the service publicly. Code changes cannot change passwords in an already-running database automatically.

## Repository data and secrets

Database exports, user records, password hashes, test attempts, and archive backups must stay outside source control. Store backups in access-controlled storage with encryption and a retention policy. The `database_export` directory is ignored; only its explanatory README is tracked.

Removing export files from the current branch does not remove them from older Git commits. If any export contains real user data, credentials, or production-derived information, coordinate a history rewrite to purge those paths from all refs and ask collaborators to re-clone. Rotate credentials that might have been exposed in a clone or backup.

## Remaining deployment controls

- Apply request-body size limits and distributed rate limiting at a trusted reverse proxy/WAF. The in-process limiters are supplemental and reset when a worker restarts.
- Use HTTPS at the reverse proxy and restrict database network access to the application hosts.
- Run automated dependency scanning and application tests before deployment.
- Verify that MongoDB backups, application logs, and environment files are not served from the frontend/static directory.
