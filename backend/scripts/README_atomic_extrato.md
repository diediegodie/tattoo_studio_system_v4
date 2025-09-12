# Atomic Transaction Extrato Generation

## Overview

This enhancement adds atomic transaction support to the extrato generation process. The system now ensures data consistency by wrapping the entire transfer process in a single database transaction, with automatic rollback on any failures.

## Key Features

### ✅ **Atomic Transactions**
- Entire extrato generation process wrapped in a single transaction
- Automatic rollback if any step fails
- Data consistency guaranteed

### ✅ **Backup Verification**
- Backup must exist and be valid before data transfer begins
- Prevents data loss by ensuring backup is available
- Comprehensive logging of verification steps

### ✅ **Safe Historical Data Deletion**
- Modular deletion function with proper dependency order
- Comprehensive error handling and logging
- Modular and testable design

### ✅ **Transparent Batch Processing**
- Automatic batching of large datasets for optimal performance
- Maintains transaction integrity across batches
- Comprehensive error handling and logging
- Transparent to end users

### ✅ **Error Handling**
- Database errors trigger automatic rollback
- Unexpected exceptions are caught and logged
- Session cleanup ensures no resource leaks

### ✅ **Comprehensive Logging**
- All steps logged with timestamps
- Success/failure status tracking
- Detailed error information

## Architecture

### Core Functions

#### `verify_backup_before_transfer(year, month)`
- Verifies backup exists and is valid
- Returns `True` if backup is ready, `False` otherwise
- Logs verification results

#### `generate_extrato_with_atomic_transaction(mes, ano, force=False)`
- Main atomic transaction function
- Wraps entire process in database transaction
- Handles rollback on failures
- Returns `True` on success, `False` on failure

#### `delete_historical_records_atomic(db_session, pagamentos, sessoes, comissoes, gastos, mes, ano)`
- Safely deletes historical records within transaction
- Handles dependency order and circular references
- Comprehensive error handling and logging
- Modular and testable design

#### `process_records_in_batches(records, batch_size, process_func, *args, **kwargs)`
- Processes records in configurable batches
- Maintains transaction integrity across batches
- Comprehensive error handling and logging
- Transparent to end users

#### `get_batch_size()`
- Retrieves batch size from environment variable
- Defaults to 100 records per batch
- Configurable via `BATCH_SIZE` environment variable

#### `check_and_generate_extrato_with_transaction(mes=None, ano=None, force=False)`
- High-level function for extrato generation
- Handles monthly automation logic
- Includes backup verification
- Logs run status to database

## Usage

### Manual Generation

```bash
# Generate for specific month with atomic transaction
python scripts/run_atomic_extrato.py --year 2025 --month 9

# Force generation (overwrite existing)
python scripts/run_atomic_extrato.py --year 2025 --month 9 --force

# Monthly automation (uses previous month)
python scripts/run_atomic_extrato.py
```

### Automated Generation

```bash
# Run the atomic extrato script
./scripts/run_atomic_extrato.sh

# Or schedule via CRON (recommended):
# 0 2 1 * * /path/to/backend/scripts/run_atomic_extrato.sh
```

### Testing

```bash
# Test atomic functionality
python scripts/test_atomic_extrato.py

# Test with specific month
python scripts/test_atomic_extrato.py --year 2025 --month 9
```

## Transaction Flow

```
1. Backup Verification
   ↓
2. Begin Transaction
   ↓
3. Query Historical Data
   ↓
4. Serialize Data
   ↓
5. Calculate Totals
   ↓
6. Create Extrato Record
   ↓
7. Delete Original Records
   ↓
8. Commit Transaction
   ↓
9. Log Success
```

## Error Scenarios & Rollback

The system handles these error scenarios with automatic rollback:

### Database Errors
- Connection failures
- Constraint violations
- Deadlock situations

### Application Errors
- JSON serialization failures
- Data validation errors
- Unexpected exceptions

### Backup Errors
- Missing backup files
- Corrupted backup files
- Permission issues

## Logging

### Log Files
- `logs/atomic_extrato.log`: Main operation logs
- `logs/atomic_extrato_cron.log`: CRON execution logs
- `logs/backup_process.log`: Backup-related logs

### Log Levels
- `INFO`: Normal operations and success messages
- `WARNING`: Non-critical issues
- `ERROR`: Failures requiring attention

### Sample Log Output
```
2025-09-11 20:02:03,612 - __main__ - INFO - Starting atomic extrato generation for 09/2025
2025-09-11 20:02:03,612 - app.services.backup_service - INFO - ✓ Backup verification successful
2025-09-11 20:02:03,615 - app.services.extrato_service - INFO - Beginning atomic transaction
2025-09-11 20:02:03,620 - app.services.extrato_service - INFO - ✓ Atomic extrato generation completed
```

## Database Integration

### PostgreSQL Features Used
- **Transactions**: ACID compliance for data consistency
- **Foreign Keys**: Maintain referential integrity during deletions
- **JSONB**: Efficient storage of serialized data

### Session Management
- `SessionLocal()` for thread-safe database sessions
- Automatic session cleanup in `finally` blocks
- Proper commit/rollback handling

## Migration from Legacy System

### Before (Legacy)
```python
# Non-atomic, potential data loss
generate_extrato(mes, ano)
```

### After (Atomic)
```python
# Atomic with backup verification
success = generate_extrato_with_atomic_transaction(mes, ano)
```

### Integration Points
- Replace calls to `generate_extrato()` with `generate_extrato_with_atomic_transaction()`
- Update CRON jobs to use `run_atomic_extrato.sh`
- Monitor new log files for issues

## Monitoring & Troubleshooting

### Health Checks
```python
from app.services.extrato_service import verify_backup_before_transfer

# Check if backup exists for current month
backup_ok = verify_backup_before_transfer(2025, 9)
```

### Common Issues

#### Backup Not Found
```
ERROR - Backup verification failed for 09/2025
SOLUTION - Run backup creation first
```

#### Database Connection Error
```
ERROR - Database error during atomic extrato generation
SOLUTION - Check database connectivity and credentials
```

#### Transaction Timeout
```
ERROR - Transaction rolled back due to timeout
SOLUTION - Check database performance and connection pool settings
```

## Performance Considerations

### Transaction Scope
- Keep transactions as short as possible
- Batch operations where appropriate
- Monitor for long-running transactions

### Backup Verification
- File existence checks are fast
- CSV validation only reads file headers
- Minimal performance impact

## Security

### Data Protection
- Backup verification prevents accidental data loss
- Transaction rollback protects against partial updates
- Comprehensive audit logging

### Access Control
- Same authentication requirements as legacy system
- Database permissions unchanged
- File system permissions for backup access

## Future Enhancements

### Potential Improvements
- **Transaction Timeouts**: Configurable timeout settings
- **Retry Logic**: Automatic retry on transient failures
- **Progress Tracking**: Real-time progress for long operations
- **Batch Processing**: Handle large datasets in chunks

### Monitoring Enhancements
- **Metrics Collection**: Performance and success rate metrics
- **Alert System**: Email/SMS alerts on failures
- **Dashboard**: Web interface for monitoring

## Testing

### Unit Tests
```python
def test_atomic_transaction_success():
    # Test successful transaction completion

def test_atomic_transaction_rollback():
    # Test rollback on simulated failure

def test_backup_verification():
    # Test backup verification logic
```

### Integration Tests
```python
def test_full_extrato_workflow():
    # Test complete workflow with real database
```

## Conclusion

The atomic transaction implementation provides robust data consistency guarantees while maintaining the existing API and user experience. The backup verification ensures no data loss, and comprehensive error handling makes the system reliable for production use.
