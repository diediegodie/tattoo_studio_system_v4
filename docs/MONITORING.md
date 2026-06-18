# Monitoring & Logging

## Liveness

```
/api/health
```

## Readiness

```
/ready
```

## Extended Health

```
/health
```

## Internal Monitoring

```
/internal/health
```

## Logging

Log location:

```
backend/logs/
```

Main files:
- `app.log`
- `atomic_extrato.log`
- `backup_process.log`
- `sql.log`

## Metrics

Tracked metrics:
- Request duration
- Database query duration
- Job execution time
- Health check status
- Slow Query Alerts

```
ALERT_SLOW_QUERY_ENABLED=true
ALERT_QUERY_MS_THRESHOLD=500
```
