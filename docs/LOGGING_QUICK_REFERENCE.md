# Logging Quick Reference Guide

## Basic Usage

### 1. Import and Create Logger

```python
from app.core.logging_config import get_logger

logger = get_logger(__name__)
```

### 2. Log Levels

```python
# DEBUG: Detailed diagnostic information (dev only)
logger.debug("Processing user request", extra={"context": {"user_id": 123}})

# INFO: General informational messages
logger.info("User logged in successfully", extra={"context": {"email": "user@example.com"}})

# WARNING: Warning messages for unexpected but recoverable situations
logger.warning("Rate limit approaching", extra={"context": {"requests": 95, "limit": 100}})

# ERROR: Error messages for failures
logger.error("Failed to process payment", extra={"context": {"order_id": 456, "error": "timeout"}})

# CRITICAL: Critical failures requiring immediate attention
logger.critical("Database connection lost", extra={"context": {"retries": 3}})
```

### 3. Log with Context (RECOMMENDED)

Always use the `extra={"context": {...}}` pattern for structured logging:

```python
logger.info(
    "Extrato processed successfully",
    extra={
        "context": {
            "mes": 9,
            "ano": 2025,
            "user_id": 1,
            "duration_ms": 125.4,
            "record_count": 45,
        }
    },
)
```

### 4. Log Exceptions

Use `logger.exception()` to automatically capture stack traces:

```python
try:
    result = risky_operation()
except Exception as e:
    logger.exception(
        "Operation failed",
        extra={"context": {"operation": "risky_operation", "error": str(e)}},
    )
    raise
```

## Advanced Usage

### 5. Performance Logging

Use the helper function for consistent performance tracking:

```python
from app.core.logging_config import log_performance
import time

start_time = time.time()
# ... do work ...
duration_ms = (time.time() - start_time) * 1000

log_performance(
    "process_extrato",
    duration_ms,
    user_id=123,
    record_count=45,
    cache_hit=True,
)
```

### 6. SQL Query Logging

Use the helper for manual SQL query logging:

```python
from app.core.logging_config import log_sql_query

log_sql_query(
    query="SELECT * FROM transacao WHERE mes = :mes AND ano = :ano",
    params={"mes": 9, "ano": 2025},
    duration_ms=12.34,
    row_count=45,
)
```

## Migration Examples

### Before (print statements)

```python
print(f"[DEBUG] Processing user {user_id}")
print(f"[ERROR] Failed to save: {str(e)}")
print(f"[INFO] Found {len(results)} results")
```

### After (structured logging)

```python
logger.debug("Processing user", extra={"context": {"user_id": user_id}})

logger.error(
    "Failed to save",
    extra={"context": {"error": str(e)}},
    exc_info=True,  # Include stack trace
)

logger.info(
    "Query completed",
    extra={"context": {"result_count": len(results)}},
)
```

## Log Output Formats

### Development (Colored Console)

```
2025-01-28 15:30:45 | INFO     | app.controllers.extrato_core | Extrato processed successfully
2025-01-28 15:30:46 | WARNING  | app.services.oauth_service | Token expiring soon
2025-01-28 15:30:47 | ERROR    | app.repositories.user_repo | User not found
```

### Production (JSON)

```json
{
  "timestamp": "2025-01-28T15:30:45.123456Z",
  "level": "INFO",
  "logger": "app.controllers.extrato_core",
  "message": "Extrato processed successfully",
  "module": "extrato_core",
  "function": "process_extrato",
  "line": 145,
  "context": {
    "mes": 9,
    "ano": 2025,
    "user_id": 1,
    "duration_ms": 125.4,
    "record_count": 45
  }
}
```

## Configuration

### Environment-Based Setup

In `main.py`, logging is automatically configured based on `FLASK_ENV`:

```python
# .env for development
FLASK_ENV=development  # → DEBUG level, colored console, SQL echo

# .env for production
FLASK_ENV=production   # → INFO level, JSON format, no SQL echo
```

### Manual Configuration

```python
from app.core.logging_config import setup_logging

setup_logging(
    app=app,
    log_level=logging.INFO,  # or "INFO"
    enable_sql_echo=True,     # Enable SQLAlchemy query logging
    log_to_file=True,         # Write to logs/tattoo_studio.log
    use_json_format=False,    # False = colored console, True = JSON
)
```

## File Locations

- **General logs**: `backend/logs/tattoo_studio.log` (10MB rotation, 5 backups)
- **Error logs**: `backend/logs/tattoo_studio_errors.log` (10MB rotation, 5 backups)
- **Config module**: `backend/app/core/logging_config.py`

## Viewing Logs

### Development

Logs appear in colored console output automatically.

### Production

```bash
# Tail general logs with JSON parsing
tail -f logs/tattoo_studio.log | jq .

# Tail error logs
tail -f logs/tattoo_studio_errors.log | jq .

# Filter for specific context
tail -f logs/tattoo_studio.log | jq 'select(.context.user_id == 1)'

# Filter by log level
tail -f logs/tattoo_studio.log | jq 'select(.level == "ERROR")'
```

## Common Patterns

### Controller Actions

```python
from app.core.logging_config import get_logger

logger = get_logger(__name__)

@app.route("/extrato/api")
def extrato_api():
    mes = request.args.get("mes", type=int)
    ano = request.args.get("ano", type=int)
    
    logger.info(
        "Extrato API request received",
        extra={"context": {"mes": mes, "ano": ano}},
    )
    
    try:
        result = process_extrato(mes, ano)
        logger.info(
            "Extrato processed",
            extra={"context": {"mes": mes, "ano": ano, "record_count": len(result)}},
        )
        return jsonify(result)
    except Exception as e:
        logger.exception(
            "Extrato processing failed",
            extra={"context": {"mes": mes, "ano": ano, "error": str(e)}},
        )
        return jsonify({"error": "Internal error"}), 500
```

### Service Layer

```python
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class ExtratoService:
    def process_extrato(self, mes: int, ano: int):
        logger.debug(
            "Starting extrato processing",
            extra={"context": {"mes": mes, "ano": ano}},
        )
        
        # ... processing logic ...
        
        logger.info(
            "Extrato processing complete",
            extra={
                "context": {
                    "mes": mes,
                    "ano": ano,
                    "transactions": len(transactions),
                }
            },
        )
        
        return result
```

### Repository Layer

```python
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class TransacaoRepository:
    def get_by_month(self, mes: int, ano: int):
        logger.debug(
            "Querying transactions",
            extra={"context": {"mes": mes, "ano": ano}},
        )
        
        query = select(Transacao).where(
            Transacao.mes == mes,
            Transacao.ano == ano,
        )
        
        results = self.db.execute(query).scalars().all()
        
        logger.debug(
            "Query completed",
            extra={"context": {"mes": mes, "ano": ano, "count": len(results)}},
        )
        
        return results
```

## Best Practices

1. **Always use `extra={"context": {...}}`** for structured data
2. **Use appropriate log levels**: DEBUG for diagnostics, INFO for events, WARNING for anomalies, ERROR for failures
3. **Include relevant context**: user_id, order_id, duration_ms, error messages
4. **Use `logger.exception()` in except blocks** to capture stack traces
5. **Don't log sensitive data**: passwords, tokens, credit cards, SSNs
6. **Keep messages concise**: "User logged in" not "The user with ID 123 has successfully logged in to the system"
7. **Log at boundaries**: controller entry/exit, service start/end, database queries
8. **Use consistent field names**: `user_id` not `userId`, `duration_ms` not `time`

## Debugging Tips

### Enable Debug Logging Temporarily

```python
import logging
logging.getLogger("app.controllers.extrato_core").setLevel(logging.DEBUG)
```

### Check Current Log Level

```python
import logging
logger = logging.getLogger("app")
print(f"Current level: {logger.level}")  # 10=DEBUG, 20=INFO, 30=WARNING, etc.
```

### Test Logging Configuration

```python
from app.core.logging_config import get_logger

logger = get_logger("test")
logger.debug("This is a debug message")
logger.info("This is an info message")
logger.warning("This is a warning message")
logger.error("This is an error message")
```

---

**Last Updated**: 2025-01-28  
**Version**: 1.0.0
