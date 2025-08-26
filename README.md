# Tattoo Studio System

Management system for tattoo studios — Flask backend, PostgreSQL database, Google OAuth and a responsive frontend.

## Quick overview
- Backend: `backend/` (Flask + SQLAlchemy)
- Frontend: `frontend/` (templates, CSS, JS)
- Orchestration: `docker-compose.yml`
- Env template: `.env.example`
- Dependencies: `requirements.txt`

---

## Quick Installation (Docker)

1. Copy env file:
```bash
cp .env.example .env
```

2. Edit .env with your real credentials (see "Environment Variables" below).

3. Start services:
```bash
docker-compose up -d
```

4. Open the app at: http://localhost:5000/

---

## Local development (without Docker)

1. Create & activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy .env.example to .env and edit required values.

4. Run the app locally:
```bash
python app.py
```

(Alternatively, set FLASK_APP and use flask run from the appropriate working directory — the project uses an app factory in backend/app/main.py and the convenience runner in backend/app/app.py.)

---

## Environment Variables (required / important)

Set these in .env or your environment. Defaults shown are for development only.

DATABASE_URL (e.g. [REDACTED_DATABASE_URL])
POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
FLASK_SECRET_KEY (used by Flask for sessions) — e.g. [REDACTED_FLASK_SECRET_KEY]
JWT_SECRET_KEY (used to sign JWTs; has a dev default if not set)
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
OAUTHLIB_INSECURE_TRANSPORT (dev only, set to 1)
OAUTHLIB_RELAX_TOKEN_SCOPE (dev only, set to 1)
JOTFORM_API_KEY, JOTFORM_FORM_ID (if using JotForm sync)

See .env.example for examples.

---

## OAuth / Google setup

- Do NOT rely on the deprecated Google+ API. Configure Google OAuth / Identity credentials.
- Authorized redirect URIs (example):
http://localhost:5000/auth/google/authorized
http://127.0.0.1:5000/auth/google/authorized
- Scopes requested by the app:
email
profile
https://www.googleapis.com/auth/calendar.readonly
https://www.googleapis.com/auth/calendar.events

---

## Key endpoints (paths & HTTP methods)

GET / — Login page (web)
GET /index — Dashboard (login required)
GET /auth/login — Start Google OAuth (redirect to provider)
POST /auth/login — Local email/password login (JSON API; returns token on success)
GET /logout — Web logout (clears cookie & redirects)
POST /auth/logout — API logout (clears access token cookie)
GET /clients/ — Clients list page (web)
GET /clients/sync — Trigger JotForm -> local sync (web, redirects back)
GET /clients/api/list — Clients JSON API (internal)
GET /health — Health check
GET /db-test — Database connection test

(If you use the frontend, it expects the web routes; for API clients use the /auth/* and /clients/api/* endpoints.)

---

## Database

PostgreSQL is used in docker-compose by default.
Tables can be created automatically on startup (app runner calls create_tables).
Example to query database from host (when running via docker-compose):

```bash
docker compose exec db psql -U admin -d tattoo_studio -c "SELECT id, name, email FROM users;"
```

---

## Running tests
From the repository root (after installing dev deps):
```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
```

---

## Useful Docker commands

Start: docker compose up -d --build
Stop: docker compose down
Logs: docker compose logs app -f
Run only app: docker compose up -d app
Enter app container: docker compose exec app bash