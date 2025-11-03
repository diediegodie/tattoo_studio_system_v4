"""
Test script to verify backup functionality.
Run this to ensure the backup system works correctly.
"""

import os
import sys
from datetime import datetime
from app.core.logging_config import get_logger
import pytest

# Add the app directory to the Python path
sys.path.insert(
    0, "/home/diego/documentos/github/projetos/tattoo_studio_system_v4/backend"
)

from app.services.backup_service import BackupService

logger = get_logger(__name__)


@pytest.mark.skip(reason="Script-oriented test; run via __main__ if needed")
def test_backup_service():
    """Test the backup service functionality."""
    logger.info("Testing Backup Service")

    # Initialize service
    backup_service = BackupService(backup_base_dir="test_backups")

    # Test current month backup
    now = datetime.now()
    year = now.year
    month = now.month

    logger.info("Creating backup", extra={"context": {"month": month, "year": year}})

    # Create backup
    success, message = backup_service.create_backup(year=year, month=month)

    # Assert backup creation succeeded
    assert success, f"Backup failed: {message}"
    logger.info("Backup created successfully", extra={"context": {"message": message}})

    # Verify backup exists
    exists = backup_service.verify_backup_exists(year, month)
    logger.info(
        "Backup verification",
        extra={"context": {"status": "PASS" if exists else "FAIL"}},
    )
    assert exists, "Backup verification failed: backup file does not exist"

    # Get backup info
    info = backup_service.get_backup_info(year, month)
    logger.info(
        "Backup info",
        extra={
            "context": {
                "file": info.get("file_path"),
                "size": info.get("file_size"),
                "records": info.get("record_count"),
            }
        },
    )


@pytest.mark.skip(reason="Script-oriented test; run via __main__ if needed")
def test_csv_readability():
    """Test that the CSV file is readable and properly formatted."""
    logger.info("Testing CSV Readability")

    try:
        backup_service = BackupService(backup_base_dir="test_backups")
        now = datetime.now()

        info = backup_service.get_backup_info(now.year, now.month)

        if not info["exists"]:
            logger.error("No backup file found to test")
            assert False, "Expected backup file to exist for CSV readability test"

        file_path = info["file_path"]

        # Try to read the CSV file
        import csv

        with open(file_path, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            headers = reader.fieldnames
            rows = list(reader)

        if headers is None:
            logger.error("No headers found in CSV file")
            assert False, "CSV file has no headers"

        logger.info(
            "CSV file is readable",
            extra={
                "context": {
                    "headers": len(headers),
                    "rows": len(rows),
                    "sample_headers": headers[:5],
                }
            },
        )

        # Check for required columns
        required_cols = ["type", "id", "data"]
        missing_cols = [col for col in required_cols if col not in headers]

        if missing_cols:
            logger.error(
                "Missing required columns", extra={"context": {"missing": missing_cols}}
            )
            assert False, f"Missing required columns: {missing_cols}"

        logger.info("All required columns present")

    except Exception as e:
        logger.error(
            "CSV readability test failed",
            extra={"context": {"error": str(e)}},
            exc_info=True,
        )
        raise


def cleanup_test_files():
    """Clean up test backup files."""
    logger.info("Cleaning up test files")

    import shutil

    test_dir = "test_backups"

    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
        logger.info("Test backup directory removed")
    else:
        logger.info("No test directory to clean")


def main():
    """Run all backup tests."""
    logger.info("BACKUP SYSTEM TEST SUITE", extra={"context": {"delimiter": "=" * 50}})

    try:
        # Run tests (treat assertion failures as test failures)
        backup_test = True
        csv_test = True
        try:
            test_backup_service()
        except Exception:
            backup_test = False

        try:
            test_csv_readability()
        except Exception:
            csv_test = False

        logger.info("TEST RESULTS", extra={"context": {"delimiter": "=" * 50}})
        logger.info(
            "Backup Creation",
            extra={"context": {"status": "PASS" if backup_test else "FAIL"}},
        )
        logger.info(
            "CSV Readability",
            extra={"context": {"status": "PASS" if csv_test else "FAIL"}},
        )

        if backup_test and csv_test:
            logger.info("ALL TESTS PASSED")
            return 0
        else:
            logger.error("SOME TESTS FAILED")
            return 1

    except Exception as e:
        logger.error(
            "TEST SUITE CRASHED", extra={"context": {"error": str(e)}}, exc_info=True
        )
        return 1

    finally:
        cleanup_test_files()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
