# ExamForge Firebase Hosting + Cloud Run + MongoDB Atlas

## Current architecture

- Frontend: React Create React App / CRACO in `frontend/`
- API: FastAPI (Python) in `backend/`
- Database: MongoDB via Motor
- Frontend hosting: Firebase Hosting
- API hosting: Google Cloud Run
- Database: MongoDB Atlas

Firebase Hosting serves only the compiled static frontend. It does not run the FastAPI backend.

## 1. Create/select a dedicated Google/Firebase project

1. Open https://console.firebase.google.com/ and create/select a project dedicated to ExamForge.
2. Enable Firebase Hosting.
3. In Google Cloud Console, attach a billing account and enable Cloud Run, Cloud Build, Artifact Registry, and Secret Manager APIs.
4. Install the Google Cloud CLI and Firebase CLI on your local computer.

Example setup (replace the project ID):
```bash
gcloud auth login
gcloud config set project YOUR_GOOGLE_CLOUD_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com
npm install -g firebase-tools
firebase login
firebase use --add
```

## 2. Prepare MongoDB Atlas

Use a dedicated database named `examforge` and a database user restricted to that database. Do not point ExamForge at another application's database. You may use a separate cluster or an isolated database/user on an existing cluster if that is intentional.

1. In Atlas, open **Database Access** and create a database user with read/write access only to `examforge`.
2. In **Network Access**, configure access from the API service. Cloud Run egress IPs are not necessarily static by default. For a straightforward initial setup, Atlas may require allowing access from `0.0.0.0/0`; if you do this, use a strong database password, least-privilege database user, TLS, and rotate credentials if exposed. For production, prefer controlled static egress (Cloud NAT) and allowlist only the reserved egress IP.
3. Copy the Atlas driver connection string and replace the username, password, and database as required. URL-encode special characters in the password.

Do not put the Atlas URI in React environment variables or commit it to Git.

## 3. Create production secrets in Google Secret Manager

From the repository root, create a strong JWT secret and enter the Atlas URI when prompted. Do not commit either value.

Generate a secret locally:
```bash
openssl rand -base64 48
```

Create secrets (the commands prompt for input where shown):
```bash
gcloud secrets create examforge-mongo-url --replication-policy=automatic
# Paste the Atlas URI, then press Ctrl-D (Linux/macOS) or use the platform's supported stdin method.
gcloud secrets versions add examforge-mongo-url --data-file=-

gcloud secrets create examforge-jwt-secret --replication-policy=automatic
# Paste the output of openssl rand -base64 48, then Ctrl-D.
gcloud secrets versions add examforge-jwt-secret --data-file=-
```

If you prefer, create these secrets in **Google Cloud Console → Security → Secret Manager**. Never paste secret values into GitHub Issues, chat messages, or source files.

Grant the Cloud Run runtime service account the **Secret Manager Secret Accessor** role for these two secrets. Do not grant broad project-owner permissions to the runtime identity.

## 4. Create the first administrator before production startup

Production startup intentionally fails if no administrator exists; it does not seed demo users in production. Run `backend/create_admin.py` from a trusted local environment using the same `MONGO_URL` and `DB_NAME=examforge` values. It prompts for the admin password and stores a bcrypt hash.

From the repository root, for example:
```bash
cd backend
python -m venv .venv
# Activate the environment, then:
pip install -r requirements.txt
```

Set `MONGO_URL` and `DB_NAME=examforge` in your local shell environment (do not commit a .env file), then run:
```bash
python create_admin.py --email YOUR_ADMIN_EMAIL --name "ExamForge Administrator"
```

If you have already imported data, first verify that the database is the intended ExamForge database and an admin does not already exist. Do not create duplicate production seed data.

## 5. Deploy the API to Cloud Run

First ensure the secrets exist and the Cloud Run service account can access them. Replace `YOUR_GOOGLE_CLOUD_PROJECT_ID` and `YOUR_FIREBASE_PROJECT_ID` below. Firebase Hosting commonly uses both `.web.app` and `.firebaseapp.com` origins; keep only the exact origin(s) your users will access. If a custom domain is configured, include its exact HTTPS origin too.

```bash
gcloud run deploy examforge-api \
  --source backend \
  --region asia-south1 \
  --allow-unauthenticated \
  --set-env-vars "^@^APP_ENV=production@DB_NAME=examforge@JWT_ALGORITHM=HS256@JWT_EXPIRE_HOURS=168@CORS_ORIGINS=https://YOUR_FIREBASE_PROJECT_ID.web.app,https://YOUR_FIREBASE_PROJECT_ID.firebaseapp.com" \
  --set-secrets "MONGO_URL=examforge-mongo-url:latest,JWT_SECRET=examforge-jwt-secret:latest"
```

The custom delimiter in `--set-env-vars` avoids treating the comma between CORS origins as an environment-variable separator. Add only credentials for features you have configured, such as Razorpay or email, as Secret Manager secrets. Do not put payment secret keys in frontend configuration.

Cloud Run is public at the HTTP service layer so browser requests can reach the API; application endpoints must still enforce authentication/authorization where required. The app's health endpoint is `/api/`. After deployment, get the service URL:
```bash
gcloud run services describe examforge-api --region asia-south1 --format='value(status.url)'
``

Test the API health URL by appending `/api/`. Check logs if startup fails:
```bash
gcloud run services logs read examforge-api --region asia-south1 --limit=100
``

### Important production checks

- The backend has local file uploads under `backend/uploads`. Cloud Run's writable filesystem is ephemeral; uploads can disappear after an instance replacement. Before relying on admin image uploads, migrate uploaded files to durable object storage (for example, Google Cloud Storage) and update the upload/read routes to use it. Until then, treat uploads as a known deployment limitation.
- Verify the production startup checks in `backend/server.py`. It requires a strong JWT secret and an existing admin, and rejects active default demo credentials.
- Set a deliberate minimum/maximum instance policy and concurrency after load testing. Avoid assuming a single instance or default scaling values will meet exam submission bursts.
- Review Cloud Run logs, Atlas metrics, backups, quotas and billing alerts.

## 6. Configure Firebase Hosting and GitHub Actions

This repository contains `firebase.json` and `.github/workflows/firebase-hosting.yml`. The workflow builds the React frontend and deploys `frontend/build` to Firebase Hosting on pushes to `main`.

In GitHub, open **Settings → Secrets and variables → Actions** and add:

Repository variables:
- `FIREBASE_PROJECT_ID`: the Firebase project ID.
- `REACT_APP_BACKEND_URL`: the deployed Cloud Run URL, without a trailing slash.

Repository secret:
- `FIREBASE_SERVICE_ACCOUNT`: service-account JSON for Firebase deployment. Store it only as a GitHub secret.

GitHub automatically supplies `GITHUB_TOKEN`; do not create that secret manually. The service-account key must never be committed to the repository. Grant it only the permissions needed for Hosting deployment.

Then trigger **Actions → Deploy React frontend to Firebase Hosting → Run workflow**, or push a commit to `main`. The frontend variable `REACT_APP_BACKEND_URL` is public because it is embedded in the client bundle; never put database URLs or private keys there.

## 7. Validate end to end before production use

- Confirm Firebase Hosting loads and nested React routes work on reload.
- Confirm browser requests use the Cloud Run HTTPS hostname and do not fail CORS.
- Test registration, login, logout, password reset, role restrictions, question loading, exam start, answer autosave, submit, result review, admin question management, and bulk actions.
- Test Razorpay only with test credentials first, including webhook signature validation, and configure email only if used.
- Verify file upload persistence; do not consider the deployment production-ready until uploads use durable storage.
- Confirm no database or service credentials are present in built frontend assets, Git history, logs, or public API responses.
- Monitor Cloud Run errors and latency, Atlas connection counts/storage, and costs. Test realistic concurrent exam sessions and submission bursts.

## SQLite note

SQLite is a local database file, not MongoDB Atlas. The current application uses MongoDB-specific Motor queries. Changing `MONGO_URL` to a SQLite URL will not work. Keep MongoDB Atlas for this deployment unless you plan a separate, tested database-layer migration.
