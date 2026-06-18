
# Deployment

## Infrastructure

| Component | Provider |
|------------|----------|
| Application | Render |
| Database | Neon PostgreSQL |
| CI/CD | GitHub Actions |
| Containerization | Docker |

## Deployment Flow

```text
GitHub Push
     │
     ▼
GitHub Actions
     │
     ▼
Tests
     │
     ▼
Render Deploy
```
## Environment Variables

Required:

```
DATABASE_URL=
FLASK_SECRET_KEY=
JWT_SECRET_KEY=

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

AUTHORIZED_EMAILS=
```

Optional:

```
JOTFORM_API_KEY=
JOTFORM_FORM_ID=
HEALTH_CHECK_TOKEN=
```

## CI/CD

Workflow:
```
1. Build
2. Test
3. Coverage Validation
4. Deployment
```

## Health Check

Primary endpoint:

```
/api/health
```