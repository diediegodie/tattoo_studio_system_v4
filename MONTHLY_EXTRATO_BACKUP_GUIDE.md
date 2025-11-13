# Monthly Extrato Backup Safety Net - Complete Guide

## Overview

This guide explains how your "Monthly Extrato Backup Safety Net" works and provides verification steps to ensure it will function correctly in production.

## System Architecture

### Two-Layer Automation System

Your system has **two independent automation layers** for maximum reliability:

#### 1. Primary Automation (APScheduler)
- **Location**: `backend/app/main.py` (lines 1360-1451)
- **Schedule**: Day 1 of each month at 02:00 AM (São Paulo timezone)
- **Function**: `generate_monthly_extrato_job()`
- **Control**: Environment variable `ENABLE_MONTHLY_EXTRATO_JOB=true`

#### 2. Safety Net (GitHub Actions)
- **Location**: `.github/workflows/monthly_extrato_backup.yml`
- **Schedule**: Day 2 of each month at 03:00 UTC
- **Purpose**: Backup if primary automation fails
- **Control**: Can be manually triggered via workflow_dispatch

## How It Works

### Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    MONTHLY EXTRATO PROCESS                       │
└─────────────────────────────────────────────────────────────────┘

1. HISTORICO TABLE (Source Data)
   ├── Pagamentos (Payments)
   ├── Sessoes (Sessions)
   ├── Comissoes (Commissions)
   └── Gastos (Expenses)
          ↓
2. BACKUP CREATION (CSV Export)
   └── backups/YYYY_MM/backup_YYYY_MM.csv
          ↓
3. ATOMIC TRANSACTION
   ├── Query historical data
   ├── Serialize to JSON
   ├── Calculate totals
   ├── Create extrato record
   └── Delete historical records
          ↓
4. EXTRATO TABLE (Monthly Snapshot)
   └── User filters by month/year to view
```

### Step-by-Step Process

#### APScheduler (Primary - Day 1 @ 02:00 AM São Paulo)
1. Trigger: `CronTrigger(day=1, hour=2, minute=0)`
2. Function: `generate_monthly_extrato_job()`
3. Calls: `check_and_generate_extrato_with_transaction()`
4. Target: Previous month's data
5. Backup Check: Verifies backup exists (if `EXTRATO_REQUIRE_BACKUP=true`)
6. Atomic Transaction: All-or-nothing data transfer
7. Logging: Detailed logs with correlation IDs

#### GitHub Actions (Safety Net - Day 2 @ 03:00 UTC)
1. Trigger: Scheduled cron or manual workflow_dispatch
2. Step 1: Call `/api/backup/create_service` endpoint
   - Creates CSV backup if not exists
   - Returns 200 (success) or 409 (already exists)
3. Step 2: Call `/api/extrato/generate_service` endpoint
   - Verifies backup exists
   - Generates extrato atomically
   - Returns success or error
4. On Success: Creates workflow summary
5. On Failure: Creates GitHub Issue with debug info

## Configuration Requirements

### Environment Variables

#### Backend Application (.env or Docker environment)
```bash
# Timezone (REQUIRED for correct scheduling)
TZ=America/Sao_Paulo

# Backup requirement (RECOMMENDED: true for production)
EXTRATO_REQUIRE_BACKUP=true

# Enable APScheduler job (REQUIRED for primary automation)
ENABLE_MONTHLY_EXTRATO_JOB=true

# Database connection
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# JWT Secret (REQUIRED for service account tokens)
JWT_SECRET_KEY=your-secure-secret-key-here

# Flask Secret
FLASK_SECRET_KEY=your-flask-secret-key-here
```

#### GitHub Secrets (REQUIRED for workflow)

You must configure these secrets in GitHub:
**Settings → Secrets and variables → Actions → New repository secret**

1. **EXTRATO_API_BASE_URL**
   - Description: Base URL of your production backend
   - Example: `https://your-api-domain.com`
   - Do NOT include trailing slash

2. **EXTRATO_API_TOKEN**
   - Description: Long-lived JWT token for service account
   - See "Creating Service Account Token" section below
   - Must belong to user with admin permissions

## Creating Service Account Token

### Step 1: Ensure Service Account Exists

The service account is automatically created on app startup via `ensure_service_account_user()` in `backend/app/db/seed.py`:

```python
# Service Account Details
user_id: 999
email: "service-account@github-actions.internal"
name: "GitHub Actions Service Account"
role: "admin"
is_active: True
```

### Step 2: Generate Long-Lived JWT Token

Run this script on your production server:

```bash
# SSH into your production server
ssh your-production-server

# Navigate to app directory
cd /path/to/tattoo_studio_system_v4

# Run token generation script
docker-compose exec app python -c "
from app.core.security import create_access_token
from datetime import timedelta

# Generate token that expires in 10 years (for automation)
token = create_access_token(
    user_id=999,
    email='service-account@github-actions.internal',
    expires_delta=timedelta(days=3650)  # 10 years
)
print('Copy this token to EXTRATO_API_TOKEN secret:')
print(token)
"
```

### Step 3: Add Token to GitHub Secrets

1. Copy the generated token
2. Go to your GitHub repository
3. Navigate to: **Settings → Secrets and variables → Actions**
4. Click **New repository secret**
5. Name: `EXTRATO_API_TOKEN`
6. Value: Paste the token
7. Click **Add secret**

### Step 4: Add API Base URL

1. Go to: **Settings → Secrets and variables → Actions**
2. Click **New repository secret**
3. Name: `EXTRATO_API_BASE_URL`
4. Value: Your production API URL (e.g., `https://api.yourdomain.com`)
5. Click **Add secret**

## Verification Steps

### 1. Verify Service Account Exists

```bash
# SSH into production server
docker-compose exec app python -c "
from app.db.session import SessionLocal
from app.db.base import User

with SessionLocal() as db:
    user = db.get(User, 999)
    if user:
        print('✓ Service account exists')
        print(f'  Email: {user.email}')
        print(f'  Name: {user.name}')
        print(f'  Active: {user.is_active}')
    else:
        print('✗ Service account NOT found')
"
```

### 2. Verify JWT Token Works

```bash
# Test the token locally (replace with your values)
curl -v -X POST "https://your-api.com/api/extrato/generate_service" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{"month": 10, "year": 2025, "force": false}'
```

Expected response:
- HTTP 200: Success
- HTTP 401: Token invalid or expired
- HTTP 500: Server error (check logs)

### 3. Verify GitHub Secrets Configured

```bash
# You cannot view secret values, but you can verify they exist
# Go to: Settings → Secrets and variables → Actions
# You should see:
# - EXTRATO_API_BASE_URL
# - EXTRATO_API_TOKEN
```

### 4. Test Manual Workflow Trigger

1. Go to **Actions** tab in GitHub
2. Click **Monthly Extrato Backup Safety Net**
3. Click **Run workflow**
4. Fill in parameters:
   - Month: (e.g., 10)
   - Year: (e.g., 2025)
   - Force: false
5. Click **Run workflow**
6. Watch the workflow execution
7. Check workflow summary and logs

### 5. Verify APScheduler is Running

```bash
# Check logs for APScheduler registration
docker-compose logs app | grep "Monthly extrato job registered"

# Should see:
# Monthly extrato job registered - job_id: monthly_extrato, schedule: day 1 at 02:00 AM
```

### 6. Verify Backup Directory Exists

```bash
# Check if backups directory exists and is writable
docker-compose exec app ls -la /app/backups/

# If it doesn't exist or has permission issues:
mkdir -p backups
chmod -R 777 backups
```

## Testing the Workflow

### Test Script

Use the provided test script to verify the workflow locally:

```bash
# Copy .env.example to .env and add your credentials
cp .env.example .env

# Edit .env and add:
# EXTRATO_API_BASE_URL=https://your-api.com
# EXTRATO_API_TOKEN=your_jwt_token_here

# Run the test script
./test_workflow_locally.sh 10 2025 false

# Parameters:
# - Month: 10 (October)
# - Year: 2025
# - Force: false (don't regenerate if exists)
```

### Manual API Testing

#### Step 1: Create Backup
```bash
curl -X POST "https://your-api.com/api/backup/create_service" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"month": 10, "year": 2025}'
```

Expected responses:
- 200: Backup created successfully
- 409: Backup already exists (OK)
- 401: Unauthorized (check token)

#### Step 2: Generate Extrato
```bash
curl -X POST "https://your-api.com/api/extrato/generate_service" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"month": 10, "year": 2025, "force": false}'
```

Expected responses:
- 200: Extrato generated successfully
- 500: Error (check logs and backup existence)
- 401: Unauthorized (check token)

## Troubleshooting

### Common Issues

#### 1. Workflow Fails: "EXTRATO_API_BASE_URL or EXTRATO_API_TOKEN not configured"

**Cause**: GitHub secrets not set

**Solution**:
1. Go to Settings → Secrets and variables → Actions
2. Add both secrets as described above
3. Re-run workflow

#### 2. Workflow Fails: "Unauthorized" (HTTP 401)

**Cause**: Invalid or expired JWT token

**Solution**:
1. Generate new token (see "Creating Service Account Token")
2. Update `EXTRATO_API_TOKEN` secret in GitHub
3. Re-run workflow

#### 3. Workflow Fails: "Backup verification failed"

**Cause**: Backup doesn't exist and `EXTRATO_REQUIRE_BACKUP=true`

**Solution**:
Option A: Create backup first
```bash
# Manually create backup via API
curl -X POST "https://your-api.com/api/backup/create_service" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"month": 10, "year": 2025}'
```

Option B: Disable backup requirement (NOT RECOMMENDED for production)
```bash
# In .env or environment
EXTRATO_REQUIRE_BACKUP=false
```

#### 4. APScheduler Job Not Running

**Cause**: Job disabled or timezone misconfigured

**Solution**:
```bash
# Check environment variables
ENABLE_MONTHLY_EXTRATO_JOB=true  # Must be "true"
TZ=America/Sao_Paulo              # Must be correct timezone

# Restart the application
docker-compose restart app

# Check logs
docker-compose logs app | grep "Monthly extrato job"
```

#### 5. Backup Directory Permission Denied

**Cause**: Container cannot write to backups directory

**Solution**:
```bash
# On host machine
mkdir -p backups
chmod -R 777 backups

# Or in docker-compose.yml, add volume:
volumes:
  - ./backups:/app/backups
```

## Monitoring and Alerts

### Workflow Success/Failure Notifications

The workflow automatically creates GitHub Issues on failure:

**Issue Title**: "Monthly Extrato Generation Failed - MM/YYYY"

**Issue Content**:
- Workflow run link
- Error details
- Debug information
- Manual trigger commands
- Curl command for testing

### Checking Workflow History

1. Go to **Actions** tab
2. Click **Monthly Extrato Backup Safety Net**
3. View past runs (success/failure)
4. Download artifacts for debugging

### Logs and Debugging

#### Application Logs
```bash
# View real-time logs
docker-compose logs -f app

# Search for extrato generation
docker-compose logs app | grep "monthly_extrato"

# Search for specific month
docker-compose logs app | grep "10/2025"
```

#### Workflow Logs
1. Go to Actions tab
2. Click on a workflow run
3. Expand steps to see detailed logs
4. Download artifacts on failure

## Production Deployment Checklist

Before deploying to production, verify:

- [ ] `TZ=America/Sao_Paulo` set in environment
- [ ] `EXTRATO_REQUIRE_BACKUP=true` set in environment
- [ ] `ENABLE_MONTHLY_EXTRATO_JOB=true` set in environment
- [ ] Service account (user_id=999) exists in database
- [ ] JWT token generated and stored in GitHub secret `EXTRATO_API_TOKEN`
- [ ] Production API URL stored in GitHub secret `EXTRATO_API_BASE_URL`
- [ ] Backups directory exists and is writable
- [ ] Database connection working
- [ ] APScheduler job registered (check logs)
- [ ] Manual workflow trigger tested successfully
- [ ] API endpoints `/api/backup/create_service` and `/api/extrato/generate_service` working

## Security Considerations

### Service Account Token

- **Long-lived token**: Use 10-year expiration for automation
- **Dedicated account**: Never use a real user's token
- **Admin permissions**: Required for backup/extrato operations
- **Secret storage**: Store only in GitHub Secrets (never in code)
- **Rotation**: Plan to rotate token before 10-year expiration

### API Security

- JWT authentication required for all service endpoints
- Rate limiting applies (30 requests per minute for backup)
- HTTPS enforced in production
- Authorization checked on every request

### Backup Safety

- CSV backups stored locally on server
- Backup verification required before data deletion
- Atomic transactions ensure data consistency
- Rollback on any error during generation

## Support and Resources

### Key Files
- Workflow: `.github/workflows/monthly_extrato_backup.yml`
- APScheduler: `backend/app/main.py` (lines 1360-1451)
- Backup Service: `backend/app/services/backup_service.py`
- Extrato Atomic: `backend/app/services/extrato_atomic.py`
- API Endpoints: `backend/app/controllers/api_controller.py`
- Config: `backend/app/core/config.py`

### Testing Scripts
- `test_workflow_locally.sh` - Test workflow endpoints locally
- `backend/scripts/run_atomic_extrato.py` - Manual extrato generation
- `backend/scripts/check_backup_status.py` - Check backup status

### Documentation
- `README.md` - Main project documentation
- `CHANGELOG.md` - Version history
- `QUICK_START_GUIDE.md` - Quick setup guide
- This file - Complete backup workflow guide

## Conclusion

Your "Monthly Extrato Backup Safety Net" is **well-designed and production-ready** with these features:

✅ **Redundancy**: Two independent automation layers
✅ **Safety**: Backup verification before data deletion
✅ **Reliability**: Atomic transactions with rollback
✅ **Monitoring**: Automatic issue creation on failure
✅ **Flexibility**: Manual trigger with parameters
✅ **Debugging**: Comprehensive logging and artifacts

The only requirements are:
1. Configure GitHub Secrets (EXTRATO_API_BASE_URL, EXTRATO_API_TOKEN)
2. Verify service account exists and token works
3. Test manual workflow trigger once before production

After completing these steps, you can confidently deploy to production knowing your monthly extrato automation will work reliably.
