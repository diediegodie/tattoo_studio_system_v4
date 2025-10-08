"""
Script to create backup # Set up logging
log_handler = logging.FileHandler('logs/backup_process.log', mode='a')
log_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        log_handler
    ]
)

# Ensure all loggers are captured
logging.getLogger().setLevel(logging.INFO)

logger = logging.getLogger(__name__)data to CSV files.

This script:
- Uses the BackupService to create backups of historical data
- Can be run manually or scheduled via CRON
- Follows the same patterns as other scripts in the project

Usage:
- Run manually: python create_backup.py [--year YYYY] [--month MM]
- If no args, uses current month/year
- Scheduled via CRON: 0 2 1 * * /path/to/create_backup.sh

Requirements:
- Run inside the app container or with correct PYTHONPATH
- Database must be accessible
"""

import argparse
import sys
from datetime import datetime

# Add the app directory to the Python path
sys.path.insert(
    0, "/home/diego/documentos/github/projetos/tattoo_studio_system_v4/backend"
)

from app.core.logging_config import get_logger
from app.services.backup_service import BackupService

logger = get_logger(__name__)


def main():
    """Main function to create backup."""
    parser = argparse.ArgumentParser(description="Create backup of historical data")
    parser.add_argument(
        "--year", type=int, help="Year to backup (defaults to current year)"
    )
    parser.add_argument(
        "--month", type=int, help="Month to backup (defaults to current month)"
    )
    parser.add_argument(
        "--base-dir", default="backups", help="Base directory for backups"
    )

    args = parser.parse_args()

    try:
        logger.info("Starting backup script")

        # Initialize backup service
        backup_service = BackupService(backup_base_dir=args.base_dir)

        # Create backup
        success, message = backup_service.create_backup(
            year=args.year, month=args.month
        )

        if success:
            logger.info(f"Backup completed successfully: {message}")
            return 0
        else:
            logger.error(f"Backup failed: {message}")
            return 1

    except Exception as e:
        error_msg = f"Unexpected error during backup: {str(e)}"
        logger.error(error_msg)
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
