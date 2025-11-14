# Tattoo Studio System

Management system for tattoo studios — Flask backend, PostgreSQL database, Google OAuth and a responsive frontend.

## Recent Improvements

### v4.1.1 - Batch Processing & Financial Accuracy (2025-01-XX)

- **Fixed Revenue Calculation**: Corrected `calculate_totals()` in `extrato_core.py` to count payments only for revenue, eliminating double-counting of sessions + payments
- **Enhanced Test Coverage**: Comprehensive test suite with 370+ tests covering all major functionality
- **Batch Processing**: Transparent batching for large datasets during extrato generation with configurable batch sizes
- **Atomic Transactions**: Guaranteed data integrity during monthly extrato generation with automatic rollback on failures
- **Improved Logging**: Detailed operation logging with correlation IDs for better debugging and monitoring

### Key Features
- **Financial Accuracy**: Revenue calculations now accurately reflect actual money received
- **Performance**: Batch processing handles large datasets efficiently
- **Reliability**: Atomic transactions ensure data consistency
- **Monitoring**: Comprehensive logging and health checks
- **Testing**: High test coverage validates business logic correctness

---

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
HEALTH_CHECK_TOKEN (secure token for /internal/health endpoint monitoring)
AUTHORIZED_EMAILS (comma-separated list of authorized email addresses - REQUIRED for production)

See .env.example for examples.

### Timezone (TZ)
- Default: UTC (safe and deterministic for tests and local dev)
- Production: Set `TZ=America/Sao_Paulo` to use Brasília time for date windows and reports

The app reads TZ from the environment at import time (via `app.core.config.APP_TZ`).

---

## OAuth / Google setup

- Do NOT rely on the deprecated Google+ API. Configure Google OAuth / Identity credentials.
- Authorized redirect URIs (example):
http://localhost:5000/auth/google_login/authorized
http://127.0.0.1:5000/auth/google_login/authorized
http://localhost:5000/auth/calendar/google_calendar/authorized
http://127.0.0.1:5000/auth/calendar/google_calendar/authorized
- Scopes requested by the app:
For login: openid, email, profile
For calendar: calendar.readonly, calendar.events
profile
https://www.googleapis.com/auth/calendar.readonly
https://www.googleapis.com/auth/calendar.events

---

## Authorization & Security

### Email-Based Authorization

The system implements email-based authorization to control access to sensitive operations:

**Configuration:**
Set the `AUTHORIZED_EMAILS` environment variable with a comma-separated list of authorized email addresses:

```bash
AUTHORIZED_EMAILS=admin@studio.com,manager@studio.com,artist@studio.com
```

**Behavior:**
- **OAuth Login**: Users with emails NOT in the authorized list will be rejected during Google Sign-In
- **API Access**: Sensitive CRUD endpoints require both valid JWT token AND authorized email
- **Fail-Closed**: If `AUTHORIZED_EMAILS` is empty or not set, ALL users are denied access (secure default)
- **Case-Insensitive**: Email comparison is case-insensitive for convenience

**Protected Endpoints:**
The following endpoints require authorization:
- `/inventory/*` - Inventory management (POST, PUT, DELETE, PATCH)
- `/gastos/*` - Expense tracking (POST, PUT, DELETE)
- `/sessoes/*` - Session management (POST, PUT, DELETE)
- `/financeiro/*` - Financial operations (POST)
- All other CRUD operations on sensitive data

**HTTP Status Codes:**
- `401 Unauthorized`: Missing or invalid JWT token
- `403 Forbidden`: Valid token but email not authorized

**Testing Authorization:**
```bash
# Generate token for testing
python -c "from app.core.security import create_user_token; print(create_user_token(1, 'test@example.com'))"

# Test with curl
curl -X POST http://localhost:5000/inventory/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"nome":"Test","quantidade":10}'
```

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
GET /api/health — Liveness (Render health check). Always 200, lightweight, no DB. Exempt from rate limiting.
GET /health — Liveness for humans/tools. Always 200 with `{database: connected|warming_up|error}`. Exempt from rate limiting.
GET /ready — Readiness. DB connectivity check (200 if reachable, 503 otherwise). Exempt from rate limiting.
GET /health/extrato — Business monitoring (previous month snapshot presence). Exempt from rate limiting.
GET /internal/health — Secure health check with token authentication (requires X-Health-Token header)
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

## Health checks on Render

- Liveness endpoint used by Render: `/api/health` (do not change unless you change Render settings)
  - Always returns HTTP 200
  - Does not touch the database
  - Exempt from rate limiting
- Liveness (aux): `/health` — Always 200; includes a `database` field:
  - `connected`: recent successful DB ping within ~45s cache TTL
  - `warming_up`: cache is stale and we avoid blocking while Neon wakes up
  - `error`: a recent ping attempt failed within the TTL window
- Readiness: `/ready` — Performs `SELECT 1` using SQLAlchemy
  - Returns 200 if DB reachable, 503 otherwise
  - Intended for manual diagnostics or orchestrators, not Render liveness
- Monitoring: `/health/extrato` — Business-specific check; does a small ORM query

Recommendation: Configure Render health checks to hit `/api/health`.

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

---

## Atomic Transaction System

### Overview
The system includes atomic transaction support for data integrity during monthly extrato generation. This ensures that data transfers from historico tables to extrato are performed atomically with automatic rollback on failures.

### Key Features
- **Atomic Transactions**: Entire extrato generation wrapped in single database transaction
- **Backup Verification**: Backup must exist before data transfer begins
- **Automatic Rollback**: Failed operations automatically rollback to maintain data consistency
- **Comprehensive Logging**: All operations logged with timestamps and status

### Usage

#### Manual Generation
```bash
# Generate extrato for specific month
python backend/scripts/run_atomic_extrato.py --year 2025 --month 9

# Force generation (overwrite existing)
python backend/scripts/run_atomic_extrato.py --year 2025 --month 9 --force

# Monthly automation (uses previous month)
python backend/scripts/run_atomic_extrato.py
```

#### Automated Generation (CRON)
```bash
# Edit CRON table
crontab -e

# Add monthly execution (1st of each month at 2:00 AM)
0 2 1 * * /path/to/backend/scripts/cron_atomic_extrato.sh
```

### Monitoring
```bash
# Health check
python backend/scripts/monitor_atomic_extrato.py

# Generate detailed report
python backend/scripts/monitor_atomic_extrato.py --report
```

#### Slow query alerts
- SQLAlchemy queries longer than the configured threshold are logged via the `sql.alerts` logger with full context (request ID, route, user, database target).
- Use `ALERT_SLOW_QUERY_ENABLED` (default `true`) to toggle the feature.
- Set `ALERT_QUERY_MS_THRESHOLD` to the number of milliseconds before a warning is emitted. Changes take effect immediately without restarting.
- Optionally provide `ALERT_SINK_SLACK_WEBHOOK` to mirror the alert to Slack; transient sink failures are reported once per failure type and then muted.

#### Health Check Endpoints

The application provides two health check endpoints:

**Public Health Check** (`GET /health`):
- No authentication required
- Subject to rate limiting
- Returns basic service status

**Secure Health Check** (`GET /internal/health`):
- Requires `X-Health-Token` header with valid token
- Exempt from rate limiting when authenticated
- Includes database connectivity verification
- Comprehensive logging for monitoring

**Testing the secure endpoint:**
```bash
# With valid token (replace with your actual token)
curl -i -H "X-Health-Token: 309f43190ae444f560d9a2bdde5baa1f3b4a4d70759a848ab4f07b1c124aa945" \
  http://127.0.0.1:5000/internal/health

# Without token (should return 401)
curl -i http://127.0.0.1:5000/internal/health
```

**Environment Configuration:**
- Set `HEALTH_CHECK_TOKEN` in all environments (Render, GitHub Actions, local .env)
- Generate a secure token: `python3 -c "import secrets; print(secrets.token_hex(32))"`


### Testing
```bash
# Test atomic functionality
python backend/scripts/test_atomic_extrato.py

# Test deletion function specifically
python backend/scripts/test_atomic_extrato.py --test-deletion

# Test batch processing functionality
python backend/scripts/test_batch_processing.py

# Integration testing
python backend/scripts/test_atomic_integration.py

# Health check only
python backend/scripts/test_atomic_integration.py --health-check

# Dry run (no actual database changes)
python backend/scripts/test_atomic_integration.py --dry-run
```

### Configuration

#### Batch Processing
The system automatically processes large datasets in configurable batches:

```bash
# Set batch size via environment variable
export BATCH_SIZE=50

# Or in .env file
BATCH_SIZE=50
```

**Default batch size**: 100 records per batch
**Minimum batch size**: 1 record per batch
**Environment variable**: `BATCH_SIZE`

### Demonstration
```bash
# Run batch processing demonstration
python backend/scripts/demo_batch_processing.py

# Shows how batch processing works transparently
# Demonstrates configuration options
# Includes performance examples
```

### Files
- `backend/scripts/run_atomic_extrato.py` - Main execution script
- `backend/scripts/cron_atomic_extrato.sh` - CRON wrapper script
- `backend/scripts/test_atomic_extrato.py` - Test script
- `backend/scripts/test_atomic_deletion.py` - Deletion function unit tests
- `backend/scripts/test_batch_processing.py` - Batch processing unit tests
- `backend/scripts/test_atomic_integration.py` - Integration test suite
- `backend/scripts/demo_batch_processing.py` - Batch processing demonstration
- `backend/scripts/monitor_atomic_extrato.py` - Health monitoring script
- `backend/scripts/README_atomic_extrato.md` - Detailed documentation
- `backend/scripts/cron_config.txt` - CRON configuration examples
- `backend/scripts/logrotate_atomic_extrato.conf` - Log rotation config

### Logs
- `backend/logs/atomic_extrato.log` - Main operation logs
- `backend/logs/atomic_extrato_cron.log` - CRON execution logs
- `backend/logs/backup_process.log` - Backup-related logs

For detailed information, see `backend/scripts/README_atomic_extrato.md`.