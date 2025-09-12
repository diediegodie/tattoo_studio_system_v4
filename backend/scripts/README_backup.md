# Backup System Documentation

## Overview

The backup system creates CSV files containing all historical data from the tattoo studio system. This ensures data integrity before any cleanup or transfer operations.

## Features

- **Complete Data Export**: Exports all data from `pagamentos`, `sessoes`, `comissoes`, and `gastos` tables
- **Excel Compatible**: CSV files are properly formatted and readable by Excel
- **Organized Storage**: Files are stored in `backups/YYYY_MM/` directories
- **Error Handling**: Comprehensive logging and error recovery
- **Validation**: Verifies backup integrity after creation

## File Structure

```
backups/
├── 2024_09/
│   └── backup_2024_09.csv
├── 2024_10/
│   └── backup_2024_10.csv
└── 2024_11/
    └── backup_2024_11.csv
```

## CSV Format

The backup CSV contains the following columns:
- `type`: Record type (pagamento, sessao, comissao, gasto)
- `id`: Primary key of the record
- `data`: Date of the record
- `valor`: Value/amount
- `forma_pagamento`: Payment method
- `observacoes`: Notes/observations
- `cliente_name`: Client name
- `artista_name`: Artist name
- `created_at`: Creation timestamp
- `updated_at`: Update timestamp
- Additional type-specific fields

## Usage

### Manual Backup

```bash
# Backup current month
python scripts/create_backup.py

# Backup specific month
python scripts/create_backup.py --year 2024 --month 9

# Backup with custom directory
python scripts/create_backup.py --base-dir /path/to/backups
```

### Automated Backup

```bash
# Run the backup script
./scripts/run_backup.sh

# Or directly with Python
python scripts/create_backup.py
```

### CRON Setup

Add to crontab for monthly backups:

```bash
# Backup on the 1st of every month at 2 AM
0 2 1 * * /path/to/tattoo_studio_system_v4/backend/scripts/run_backup.sh
```

## Integration with Data Cleanup

The backup system is designed to be used **before** any data cleanup operations:

```python
from app.services.backup_service import BackupService

# 1. Create backup first
backup_service = BackupService()
success, message = backup_service.create_backup()

if success:
    # 2. Only proceed with cleanup if backup was successful
    perform_data_cleanup()
else:
    # Handle backup failure
    log_error(f"Backup failed: {message}")
    raise Exception("Cannot proceed with cleanup - backup failed")
```

## Verification

### Check if Backup Exists

```python
from app.services.backup_service import BackupService

backup_service = BackupService()
exists = backup_service.verify_backup_exists(2024, 9)
print(f"Backup exists: {exists}")
```

### Get Backup Information

```python
info = backup_service.get_backup_info(2024, 9)
print(f"File: {info['file_path']}")
print(f"Size: {info['file_size']} bytes")
print(f"Records: {info['record_count']}")
```

## Error Handling

The system includes comprehensive error handling:

- **File System Errors**: Handles permission issues, disk space, etc.
- **Database Errors**: Manages connection issues and query failures
- **Data Validation**: Ensures data integrity before and after backup
- **Logging**: All operations are logged to `logs/backup_process.log`

## Security Considerations

- Backup files contain sensitive financial data
- Ensure backup directory has appropriate permissions
- Consider encrypting backup files for production use
- Regularly backup the backup files themselves

## Troubleshooting

### Common Issues

1. **Permission Denied**: Ensure write permissions on backup directory
2. **Database Connection Failed**: Check database configuration
3. **No Data Found**: Verify date range and data existence
4. **File Already Exists**: Use different month/year or remove existing file

### Logs

Check the following log files:
- `logs/backup_process.log`: Detailed operation logs
- `logs/backup_cron.log`: CRON execution logs

## Testing

Run the backup script in a test environment first:

```bash
# Test with current data
python scripts/create_backup.py --year 2024 --month 9

# Verify the CSV file was created and is readable
ls -la backups/2024_09/
head backups/2024_09/backup_2024_09.csv
```</content>
<parameter name="filePath">/home/diego/documentos/github/projetos/tattoo_studio_system_v4/backend/scripts/README_backup.md
