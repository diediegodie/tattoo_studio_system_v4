# Tattoo Studio Management System

[![CI/CD Pipeline](https://github.com/diediegodie/tattoo_studio_system_v4/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/diediegodie/tattoo_studio_system_v4/actions/workflows/ci-cd.yml)
[![Monthly Backup](https://github.com/diediegodie/tattoo_studio_system_v4/actions/workflows/monthly_extrato_backup.yml/badge.svg)](https://github.com/diediegodie/tattoo_studio_system_v4/actions/workflows/monthly_extrato_backup.yml)
[![Keep Alive](https://github.com/diediegodie/tattoo_studio_system_v4/actions/workflows/keep_alive.yml/badge.svg)](https://github.com/diediegodie/tattoo_studio_system_v4/actions/workflows/keep_alive.yml)

A comprehensive management platform built for tattoo studios, streamlining client relationships, session scheduling, inventory tracking, and financial operations. Designed for reliability, security, and ease of use.

## Overview

This system provides tattoo studio owners and artists with a centralized platform to manage their business operations. From client intake through JotForm integration to automated monthly financial statements, the application handles the complete workflow of a modern tattoo studio.

**Key Capabilities:**
- **Client Management**: Centralized client database with automatic synchronization from JotForm submissions
- **Session Tracking**: Comprehensive session records including artist, client, services, and payment details
- **Inventory Control**: Real-time inventory management with low-stock alerts
- **Financial Operations**: Automated expense tracking, revenue calculation, and monthly statement generation
- **Secure Authentication**: Google OAuth 2.0 integration with email-based authorization
- **Calendar Integration**: Google Calendar sync for appointment management

## Technology Stack

**Backend:**
- **Framework**: Flask 2.x with SQLAlchemy ORM
- **Database**: PostgreSQL (Neon serverless, free tier)
- **Authentication**: Google OAuth 2.0 + JWT tokens
- **Task Scheduling**: APScheduler for automated jobs
- **API Integration**: JotForm API for client intake

**Frontend:**
- **Templates**: Jinja2 with responsive HTML/CSS
- **JavaScript**: Vanilla JS with modern ES6+ features
- **Styling**: Custom CSS with mobile-first design

**Infrastructure:**
- **Hosting**: Render (web service + cron jobs)
- **CI/CD**: GitHub Actions
- **Containerization**: Docker + Docker Compose
- **Monitoring**: Custom health checks with automated keep-alive

## Features

### Client Management
- Automatic client import from JotForm submissions
- Client profile management with contact information
- Session history tracking per client
- Search and filter capabilities

### Session & Appointment Tracking
- Detailed session records (artist, client, service, pricing)
- Payment status tracking
- Integration with Google Calendar
- Session-to-client relationship management

### Inventory Management
- Product stock tracking
- Low-stock alerts
- Usage history
- CRUD operations with authorization

### Financial Operations
- Automated monthly statement generation
- Revenue and expense tracking
- Batch processing for large datasets
- Atomic transactions with automatic rollback
- Historical data archival

### Security & Authorization
- Google OAuth 2.0 authentication
- Email-based authorization system
- JWT token management
- Rate limiting on sensitive endpoints
- Secure session handling

### Automation & Monitoring
- **Keep-Alive Workflow**: Pings app every 14 minutes during business hours (Tue-Sat, 10:00-19:00 BRT) to prevent Render free tier spin-down
- **Monthly Statement Backup**: Automated monthly financial snapshot generation on the 2nd of each month
- **Health Checks**: Multiple endpoints for liveness, readiness, and business monitoring
- **Slow Query Alerts**: Configurable thresholds with optional Slack integration

## Recent Improvements

### v4.1.1 - Batch Processing & Financial Accuracy

- **Fixed Revenue Calculation**: Corrected double-counting in financial totals
- **Enhanced Test Coverage**: 370+ tests covering all major functionality
- **Batch Processing**: Transparent batching for large datasets with configurable batch sizes
- **Atomic Transactions**: Guaranteed data integrity during monthly operations
- **Improved Logging**: Detailed operation logging with correlation IDs for better debugging

## Project Structure

```
tattoo_studio_system_v4/
├── backend/
│   ├── app/
│   │   ├── controllers/      # HTTP request handlers
│   │   ├── core/             # Configuration, security, utilities
│   │   ├── models/           # SQLAlchemy models
│   │   ├── repositories/     # Data access layer
│   │   ├── services/         # Business logic
│   │   └── main.py           # Flask app factory
│   ├── scripts/              # Automation scripts
│   ├── migrations/           # Database migrations
│   └── tests/                # Pytest test suite
├── frontend/
│   ├── templates/            # Jinja2 HTML templates
│   └── assets/               # Static CSS/JS
├── .github/
│   └── workflows/            # GitHub Actions CI/CD
├── docs/                     # Documentation
├── docker-compose.yml        # Local development orchestration
└── requirements.txt          # Python dependencies
```

## Getting Started

### Prerequisites

- Docker & Docker Compose (recommended)
- Python 3.11+ (for local development without Docker)
- PostgreSQL 14+ (if running without Docker)
- Git

### Quick Start with Docker

1. **Clone the repository:**
   ```bash
   git clone https://github.com/diediegodie/tattoo_studio_system_v4.git
   cd tattoo_studio_system_v4
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and set required values:
   ```bash
   # Database (Neon or local PostgreSQL)
   DATABASE_URL=postgresql://user:password@host:5432/database
   POSTGRES_USER=admin
   POSTGRES_PASSWORD=secure_password
   POSTGRES_DB=tattoo_studio
   
   # Flask
   FLASK_SECRET_KEY=your-secret-key-here
   JWT_SECRET_KEY=your-jwt-secret-here
   
   # Google OAuth
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   
   # Authorization (required for production)
   AUTHORIZED_EMAILS=admin@studio.com,manager@studio.com
   
   # Optional: JotForm Integration
   JOTFORM_API_KEY=your-api-key
   JOTFORM_FORM_ID=your-form-id
   
   # Optional: Monitoring
   HEALTH_CHECK_TOKEN=your-secure-token
   ```

3. **Start the application:**
   ```bash
   docker-compose up -d
   ```

4. **Access the application:**
   - Open your browser to `http://localhost:5000`
   - Sign in with an authorized Google account

5. **View logs:**
   ```bash
   docker-compose logs -f app
   ```

### Local Development (Without Docker)

1. **Create and activate virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Set up database:**
   ```bash
   # Ensure PostgreSQL is running
   # Tables are created automatically on first run
   ```

5. **Run the application:**
   ```bash
   cd backend
   python app/app.py
   ```

6. **Access at `http://localhost:5000`**

### Running Tests

```bash
# Activate virtual environment
source venv/bin/activate

# Install development dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=backend/app --cov-report=html

# Run specific test file
pytest backend/tests/test_auth.py -v
```

## Deployment

### Render Configuration

The application is deployed on [Render](https://render.com) with the following setup:

**Web Service:**
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `cd backend && python app/app.py`
- **Plan**: Free tier (spins down after 15 minutes of inactivity)
- **Health Check**: `/api/health` (lightweight, always returns 200)

**Database:**
- **Provider**: Neon PostgreSQL (serverless, free tier)
- **Connection**: Via `DATABASE_URL` environment variable
- **Auto-sleep**: 5 minutes of inactivity

**Environment Variables:**
Configure the following in Render dashboard:
- `DATABASE_URL` - Neon PostgreSQL connection string
- `FLASK_SECRET_KEY` - Session encryption key
- `JWT_SECRET_KEY` - JWT token signing key
- `GOOGLE_CLIENT_ID` - OAuth client ID
- `GOOGLE_CLIENT_SECRET` - OAuth client secret
- `AUTHORIZED_EMAILS` - Comma-separated list of allowed emails
- `HEALTH_CHECK_TOKEN` - Secure token for internal monitoring
- `TZ=America/Sao_Paulo` - Timezone for date operations
- `JOTFORM_API_KEY` - (Optional) JotForm integration
- `JOTFORM_FORM_ID` - (Optional) JotForm form ID

### GitHub Actions Workflows

The project uses three automated workflows:

#### 1. CI/CD Pipeline (`ci-cd.yml`)
**Triggers**: Push to `main` or `develop`, Pull Requests

**Actions**:
- Builds Docker containers
- Runs full test suite (370+ tests)
- Validates code quality
- Reports test coverage

**Environment**: Isolated test database with seeded data

#### 2. Keep-Alive Workflow (`keep_alive.yml`)
**Schedule**: Tuesday-Saturday, 10:00-19:00 BRT (every 14 minutes)

**Purpose**:
- Prevents Render free tier from spinning down during business hours
- Pings `/api/health` endpoint (lightweight, no DB queries)
- Keeps instance warm with minimal resource usage

**Why 14 minutes?**
- Render spins down after 15 minutes of inactivity
- 14-minute intervals provide a safety margin
- Optimizes for responsiveness without waste

#### 3. Monthly Statement Backup (`monthly_extrato_backup.yml`)
**Schedule**: 2nd of each month at 03:00 UTC (00:00 BRT)

**Purpose**:
- Triggers automated monthly financial statement generation
- Archives historical data (sessions, expenses, payments) into statements
- Provides safety net for APScheduler job running on 1st at 02:00

**Process**:
1. Calculates previous month automatically
2. Calls `/admin/extrato/trigger` API endpoint
3. Verifies backup exists before data transfer
4. Executes atomic transaction with rollback protection
5. Creates GitHub issue if operation fails

**Manual Trigger**: Can be run manually via GitHub Actions UI with custom month/year

### Deployment Workflow

1. **Code Changes**:
   ```bash
   git add .
   git commit -m "feat: description of changes"
   git push origin main
   ```

2. **Automatic CI/CD**:
   - GitHub Actions runs tests
   - On success, Render detects push to `main`
   - Render automatically deploys new version

3. **Monitoring**:
   - Check deployment status in Render dashboard
   - Monitor logs: `https://dashboard.render.com/web/[service-id]/logs`
   - Verify health: `https://your-app.onrender.com/health`

### Health Check Endpoints

- **`/api/health`** - Liveness check (always 200, no DB)
- **`/health`** - Extended health with DB status (`connected` | `warming_up` | `error`)
- **`/ready`** - Readiness check (performs `SELECT 1` query)
- **`/health/extrato`** - Business monitoring (checks previous month snapshot)
- **`/internal/health`** - Secure monitoring with token authentication

## API Documentation

### Authentication

The application uses a dual authentication system:

**Web Interface:**
- Google OAuth 2.0 for user login
- Session cookies for authenticated requests
- Automatic redirect to OAuth provider

**API Endpoints:**
- JWT tokens for programmatic access
- Bearer token in Authorization header
- Email-based authorization check

### Key Endpoints

#### Authentication
- `POST /auth/login` - Authenticate with email/password, returns JWT token
- `GET /auth/login` - Start Google OAuth flow (web)
- `POST /auth/logout` - Invalidate JWT token
- `GET /logout` - Web logout (clears session)

#### Clients
- `GET /clients/` - Client management page (web)
- `GET /clients/api/list` - List all clients (JSON)
- `GET /clients/sync` - Trigger JotForm sync
- `POST /clients/` - Create new client (requires auth)
- `PUT /clients/<id>` - Update client (requires auth)
- `DELETE /clients/<id>` - Delete client (requires auth)

#### Sessions
- `GET /sessoes/` - Session management page (web)
- `GET /api/sessoes` - List sessions (JSON)
- `POST /api/sessoes` - Create session (requires auth)
- `PUT /api/sessoes/<id>` - Update session (requires auth)
- `DELETE /api/sessoes/<id>` - Delete session (requires auth)

#### Inventory
- `GET /inventory/` - Inventory page (web)
- `GET /api/inventory` - List inventory items (JSON)
- `POST /inventory/` - Create item (requires auth)
- `PUT /inventory/<id>` - Update item (requires auth)
- `DELETE /inventory/<id>` - Delete item (requires auth)

#### Financial
- `GET /financeiro/` - Financial dashboard (web)
- `GET /api/financeiro/extrato/<year>/<month>` - Monthly statement (JSON)
- `POST /admin/extrato/trigger` - Trigger statement generation (admin only)

#### Health & Monitoring
- `GET /api/health` - Liveness check (always 200)
- `GET /health` - Health with DB status
- `GET /ready` - Readiness check
- `GET /internal/health` - Secure health check (requires token)

## Google OAuth Setup

### Creating OAuth Credentials

1. **Go to Google Cloud Console**: https://console.cloud.google.com/
2. **Create or select a project**
3. **Enable APIs**:
   - Google+ API (for user info)
   - Google Calendar API (for calendar integration)
4. **Configure OAuth Consent Screen**:
   - User Type: External (for testing) or Internal (for organization)
   - Add authorized domains
   - Scopes: `openid`, `email`, `profile`, `calendar.readonly`, `calendar.events`
5. **Create OAuth Client ID**:
   - Application type: Web application
   - Authorized redirect URIs:
     ```
     http://localhost:5000/auth/google_login/authorized
     http://127.0.0.1:5000/auth/google_login/authorized
     http://localhost:5000/auth/calendar/google_calendar/authorized
     https://your-app.onrender.com/auth/google_login/authorized
     https://your-app.onrender.com/auth/calendar/google_calendar/authorized
     ```

### Required Scopes

**Authentication:**
- `openid` - OpenID Connect authentication
- `email` - User email address
- `profile` - Basic profile information

**Calendar Integration:**
- `https://www.googleapis.com/auth/calendar.readonly` - Read calendar events
- `https://www.googleapis.com/auth/calendar.events` - Manage calendar events

## Security

### Email-Based Authorization

The system implements email-based authorization to control access to sensitive operations:

**Configuration:**
```bash
AUTHORIZED_EMAILS=admin@studio.com,manager@studio.com,artist@studio.com
```

**Access Control:**
- OAuth login rejects unauthorized emails during Google Sign-In
- API endpoints require valid JWT token AND authorized email
- Fail-closed security: empty `AUTHORIZED_EMAILS` denies all access
- Case-insensitive email comparison

**Protected Resources:**
- Inventory management (POST, PUT, DELETE, PATCH)
- Expense tracking (POST, PUT, DELETE)
- Session management (POST, PUT, DELETE)
- Financial operations (POST)

**HTTP Status Codes:**
- `401 Unauthorized` - Missing or invalid JWT token
- `403 Forbidden` - Valid token but unauthorized email

### Rate Limiting

Configurable rate limiting protects against abuse:
- Default: 100 requests per minute per IP
- Health check endpoints exempt from limits
- Configurable via `RATE_LIMIT_ENABLED` environment variable

### Security Features

- **JWT Tokens**: Secure token-based authentication for API access
- **Session Cookies**: HTTPOnly, Secure flags for web sessions
- **HTTPS Enforcement**: Automatic redirect in production
- **CORS Configuration**: Whitelist-based cross-origin requests
- **SQL Injection Protection**: Parameterized queries via SQLAlchemy
- **XSS Prevention**: Template auto-escaping via Jinja2
- **Secret Management**: Environment-based configuration

## Database

### Schema

The application uses PostgreSQL with the following main tables:

- **users** - User accounts and OAuth data
- **clientes** - Client information
- **sessoes** - Session records
- **historico_pagamentos** - Payment history
- **historico_gastos** - Expense history
- **inventory** - Inventory items
- **extrato** - Monthly financial statements

### Database Operations

**Connect to database (Docker):**
```bash
docker-compose exec db psql -U admin -d tattoo_studio
```

**Common queries:**
```sql
-- List all clients
SELECT id, nome, email FROM clientes ORDER BY nome;

-- Check monthly statement
SELECT * FROM extrato WHERE mes = 9 AND ano = 2025;

-- View session summary
SELECT s.id, c.nome as client, s.data_sessao, s.valor_total 
FROM sessoes s 
JOIN clientes c ON s.cliente_id = c.id 
ORDER BY s.data_sessao DESC 
LIMIT 10;
```

**Backup and restore:**
```bash
# Backup
docker-compose exec db pg_dump -U admin tattoo_studio > backup.sql

# Restore
docker-compose exec -T db psql -U admin tattoo_studio < backup.sql
```

### Migrations

Database schema changes are managed through SQLAlchemy:
- Models defined in `backend/app/models/`
- Tables created automatically on first run
- Manual migrations in `backend/migrations/` for complex changes

## Monitoring & Logging

### Application Logs

Logs are written to both console and file:
- **Location**: `backend/logs/`
- **Format**: Structured JSON with correlation IDs
- **Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL

**Log Files:**
- `app.log` - General application logs
- `atomic_extrato.log` - Monthly statement generation
- `backup_process.log` - Backup operations
- `sql.log` - Database query logs

### Performance Monitoring

**Slow Query Alerts:**
```bash
# Enable slow query logging
ALERT_SLOW_QUERY_ENABLED=true
ALERT_QUERY_MS_THRESHOLD=500

# Optional Slack integration
ALERT_SINK_SLACK_WEBHOOK=https://hooks.slack.com/services/YOUR/WEBHOOK
```

**Metrics Tracked:**
- Request duration
- Database query time
- Background job execution
- Health check response times

### Debugging

**Enable debug mode (development only):**
```bash
FLASK_ENV=development
FLASK_DEBUG=1
LOG_LEVEL=DEBUG
```

**View recent errors:**
```bash
# Last 50 errors
docker-compose logs app | grep ERROR | tail -50

# Follow logs in real-time
docker-compose logs -f app
```

## Docker Commands

### Basic Operations

```bash
# Start all services
docker-compose up -d

# Start with rebuild
docker-compose up -d --build

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# View logs
docker-compose logs -f app

# View database logs
docker-compose logs -f db
```

### Container Management

```bash
# List running containers
docker-compose ps

# Enter app container
docker-compose exec app bash

# Enter database container
docker-compose exec db bash

# Restart specific service
docker-compose restart app

# Run Django-style commands
docker-compose exec app python backend/manage.py shell
```

### Debugging

```bash
# Check container health
docker-compose ps

# Inspect container
docker inspect tattoo_studio_system_v4_app_1

# View container resources
docker stats

# Clean up unused resources
docker system prune -a
```

## Advanced Features

### Atomic Transaction System

The system includes atomic transaction support for data integrity during monthly statement generation:

**Key Features:**

- **Atomic Transactions**: Entire statement generation wrapped in single database transaction
- **Backup Verification**: Backup must exist before data transfer begins
- **Automatic Rollback**: Failed operations automatically rollback to maintain data consistency
- **Comprehensive Logging**: All operations logged with timestamps and status

**Manual Generation:**

```bash
# Generate statement for specific month
python backend/scripts/run_atomic_extrato.py --year 2025 --month 9

# Force generation (overwrite existing)
python backend/scripts/run_atomic_extrato.py --year 2025 --month 9 --force

# Monthly automation (uses previous month)
python backend/scripts/run_atomic_extrato.py
```

**Monitoring:**

```bash
# Health check
python backend/scripts/monitor_atomic_extrato.py

# Generate detailed report
python backend/scripts/monitor_atomic_extrato.py --report
```

### Batch Processing

The system automatically processes large datasets in configurable batches:

```bash
# Set batch size via environment variable
export BATCH_SIZE=50

# Or in .env file
BATCH_SIZE=50
```

**Configuration:**

- Default batch size: 100 records per batch
- Minimum batch size: 1 record per batch
- Environment variable: `BATCH_SIZE`

**Testing:**

```bash
# Test atomic functionality
python backend/scripts/test_atomic_extrato.py

# Test batch processing
python backend/scripts/test_batch_processing.py

# Integration testing
python backend/scripts/test_atomic_integration.py

# Dry run (no database changes)
python backend/scripts/test_atomic_integration.py --dry-run
```

### Script Reference

**Atomic Extrato Scripts:**

- `backend/scripts/run_atomic_extrato.py` - Main execution script
- `backend/scripts/cron_atomic_extrato.sh` - CRON wrapper script
- `backend/scripts/test_atomic_extrato.py` - Test script
- `backend/scripts/test_atomic_deletion.py` - Deletion function unit tests
- `backend/scripts/test_batch_processing.py` - Batch processing unit tests
- `backend/scripts/test_atomic_integration.py` - Integration test suite
- `backend/scripts/demo_batch_processing.py` - Batch processing demonstration
- `backend/scripts/monitor_atomic_extrato.py` - Health monitoring script
- `backend/scripts/README_atomic_extrato.md` - Detailed documentation

## Roadmap

### Planned Features

**Q1 2025:**

- Enhanced reporting dashboard with charts and analytics
- Export functionality (PDF, Excel) for financial reports
- Mobile app (React Native) for on-the-go management
- Advanced inventory alerts and reordering automation

**Q2 2025:**

- Multi-studio support with franchise management
- Artist commission tracking and automated payouts
- Customer portal for appointment booking and history
- SMS/Email notifications for appointments and updates

**Q3 2025:**

- AI-powered demand forecasting for inventory
- Integration with popular payment processors (Stripe, PayPal)
- Advanced analytics with ML-based insights
- Multi-language support (Portuguese, English, Spanish)

### Known Issues

- Neon DB free tier has 5-minute auto-sleep (mitigated by keep-alive workflow)
- Large dataset operations may be slow on free tier Render instances
- Google Calendar sync requires manual token refresh after 7 days

### Contributing

Contributions are welcome! Please feel free to submit issues, fork the repository, and create pull requests for any improvements.

**Development Workflow:**

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

**Code Standards:**

- Follow PEP 8 style guide for Python code
- Write tests for new features
- Update documentation as needed
- Use meaningful commit messages

## Documentation

Additional documentation is available in the `docs/` directory:

- `docs/SYSTEM_AUDIT_REPORT.md` - Comprehensive system audit
- `docs/PRODUCTION_READINESS_95_PERCENT.md` - Production readiness checklist
- `docs/SECURITY_CLEANUP.md` - Security review and hardening
- `docs/TASK_5_RATE_LIMITING_FINAL.md` - Rate limiting implementation
- `docs/extrato_job/README.md` - Monthly statement job details
- `docs/final_prod_sec/DEPLOYMENT_CHECKLIST.md` - Deployment checklist
- `backend/scripts/README_atomic_extrato.md` - Atomic transaction system

## Support

For questions, issues, or feature requests:

- Open an issue on GitHub
- Check the documentation in `docs/` directory
- Review existing issues for similar problems

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with Flask and SQLAlchemy
- Deployed on Render and Neon
- Inspired by modern SaaS management platforms
- Thanks to all contributors and testers
