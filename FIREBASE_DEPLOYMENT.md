# ExamForge Firebase Hosting Deployment

## Current architecture

- Frontend: React Create React App / CRACO in `frontend/`
- API: FastAPI (Python) in `backend/`
- Database: MongoDB via Motor
- Firebase Hosting serves only the compiled static frontend. It does not run this FastAPI backend.

## 1. Create/select a Firebase project

1. Open https://console.firebase.google.com/ and create or select a project dedicated to ExamForge.
2. In Firebase Console, enable Firebase Hosting.
3. In Google Cloud Console for the same project, verify billing requirements for the selected backend hosting. Firebase Hosting static site hosting can be deployed independently.

## 2. Set up the API first

Deploy `backend/` as a persistent FastAPI service on a Python-capable platform, for example Google Cloud Run. Do not upload the Python backend to Firebase Hosting as static files.

For Cloud Run, from the repository root after installing and configuring the Google Cloud CLI:

```bash
gcloud auth login
gcloud config set project YOUR_GOOGLE_CLOUD_PROJECT_ID
gcloud run deploy examforge-api --source backend --region asia-south1 --allow-unauthenticated
```

Configure these environment variables/secrets on the backend service before making the service public:
- `APP_ENV=production`
- `MONGO_URL` (secret; Atlas connection URI)
- `DB_NAME=examforge`
- `JWT_SECRET` (unique random secret, at least 32 bytes)
- `JWT_ALGORITHM=HS256`
- `JWT_EXPIRE_HOURS=168`
- `CORS_ORIGINS` (the exact Firebase Hosting origin; configure backend CORS code to enforce this value if not already wired)
- Razorpay and email credentials only if those features are configured.

**Important:** Verify service startup and configure secrets before considering deployment complete. Cloud Run requires an enabled billing account. Check current quotas and pricing; do not assume all usage is free.

Use a dedicated Atlas database/user for ExamForge. Do not reuse another app's database. Add only necessary client/service IP access where feasible; avoid broad `0.0.0.0/0` access unless you understand the exposure and use strong authentication. MongoDB Atlas requires a database user and network access configuration.

## 3. Configure GitHub Actions secrets and variables

This repository includes `.github/workflows/firebase-hosting.yml`. In GitHub, open **Settings → Secrets and variables → Actions** for this repository.

Create repository secrets:
- `FIREBASE_SERVICE_ACCOUNT`: JSON service account key created for Firebase deployment. Keep it secret; never commit it.
- `GITHUB_TOKEN` is provided automatically by GitHub Actions and should not be manually created.

Create repository variables:
- `FIREBASE_PROJECT_ID`: the Firebase project ID.
- `REACT_APP_BACKEND_URL`: the deployed API's public HTTPS base URL, without a trailing slash, e.g. `https://examforge-api-xxxxx-asia-south1.run.app`.

The workflow builds the React app with `REACT_APP_BACKEND_URL` and deploys `frontend/build` to Firebase Hosting on pushes to `main`. This variable is embedded in the client bundle and is not a secret. Never put database URLs, API secrets, or payment secret keys in frontend variables.

## 4. Deployment

After committing the configuration, set the GitHub Actions secrets/variables and push to `main`. The workflow installs dependencies, builds the React site, and publishes the build to Firebase Hosting. You can also trigger it from **GitHub → Actions → Deploy React frontend to Firebase Hosting → Run workflow**.

## 5. Validation checklist

- Open the Firebase Hosting URL and reload nested routes to confirm SPA rewrites.
- Confirm API requests use the Cloud Run/API hostname and HTTPS.
- Test signup, login, logout, question loading, exam start, answer autosave, submit, result review, and admin permissions.
- Test uploads and confirm uploaded files use durable object storage. The backend currently has a local uploads directory; local container files may not persist across instance replacements.
- Verify Razorpay with test keys, webhook signature verification, email, and password-reset flows if enabled.
- Review CORS and network access. Do not expose MongoDB connection credentials to the browser.
- Review Cloud Run logs, backend error rates, Atlas usage and backups.
- Do not announce production readiness until the full flows above pass.

## SQLite note

SQLite is a local database file, not MongoDB Atlas. The current application uses MongoDB-specific Motor queries. Changing `MONGO_URL` to a SQLite URL will not work. A SQLite migration requires changing the persistence layer and all MongoDB-specific operations, and SQLite is usually a poor fit for a horizontally scaled multi-instance API unless the database file is on a properly supported shared persistent volume with appropriate locking. Keep MongoDB Atlas for the existing code unless a deliberate database migration is planned.
