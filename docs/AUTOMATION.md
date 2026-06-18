# Automation

## APScheduler

Used for scheduled tasks.

## Monthly Statement Generation

Purpose:
- Archive monthly data
- Generate financial statements
- Preserve historical records

## Atomic Transactions
Features:
- Single transaction execution
- Rollback protection
- Backup verification

## Batch Processing
Configurable:
```env
BATCH_SIZE=50
```
Default:
100 records per batch

## Financial Backup Workflow
Process:
1. Calculate previous month
2. Verify backup
3. Generate statement
4. Archive records
5. Commit transaction

## Scripts
Main script:
```
backend/scripts/run_atomic_extrato.py
```
Monitoring:
```
backend/scripts/monitor_atomic_extrato.py
```
