"""
Test script to verify backup functionality.
Run this to ensure the backup system works correctly.
"""

import sys
import os
from datetime import datetime

# Add the app directory to the Python path
sys.path.insert(
    0, "/home/diego/documentos/github/projetos/tattoo_studio_system_v4/backend"
)

from app.services.backup_service import BackupService


def test_backup_service():
    """Test the backup service functionality."""
    print("Testing Backup Service...")

    # Initialize service
    backup_service = BackupService(backup_base_dir="test_backups")

    # Test current month backup
    now = datetime.now()
    year = now.year
    month = now.month

    print(f"Creating backup for {month:02d}/{year}...")

    # Create backup
    success, message = backup_service.create_backup(year=year, month=month)

    if success:
        print(f"✓ Backup created successfully: {message}")

        # Verify backup exists
        exists = backup_service.verify_backup_exists(year, month)
        print(f"✓ Backup verification: {'PASS' if exists else 'FAIL'}")

        # Get backup info
        info = backup_service.get_backup_info(year, month)
        print("✓ Backup info:")
        print(f"  - File: {info['file_path']}")
        print(f"  - Size: {info['file_size']} bytes")
        print(f"  - Records: {info['record_count']}")

        return True
    else:
        print(f"✗ Backup failed: {message}")
        return False


def test_csv_readability():
    """Test that the CSV file is readable and properly formatted."""
    print("\nTesting CSV Readability...")

    try:
        backup_service = BackupService(backup_base_dir="test_backups")
        now = datetime.now()

        info = backup_service.get_backup_info(now.year, now.month)

        if not info["exists"]:
            print("✗ No backup file found to test")
            return False

        file_path = info["file_path"]

        # Try to read the CSV file
        import csv

        with open(file_path, "r", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            headers = reader.fieldnames
            rows = list(reader)

        if headers is None:
            print("✗ No headers found in CSV file")
            return False

        print("✓ CSV file is readable")
        print(f"  - Headers: {len(headers)}")
        print(f"  - Rows: {len(rows)}")
        print(f"  - Sample headers: {headers[:5]}")

        # Check for required columns
        required_cols = ["type", "id", "data"]
        missing_cols = [col for col in required_cols if col not in headers]

        if missing_cols:
            print(f"✗ Missing required columns: {missing_cols}")
            return False

        print("✓ All required columns present")
        return True

    except Exception as e:
        print(f"✗ CSV readability test failed: {str(e)}")
        return False


def cleanup_test_files():
    """Clean up test backup files."""
    print("\nCleaning up test files...")

    import shutil

    test_dir = "test_backups"

    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
        print("✓ Test backup directory removed")
    else:
        print("✓ No test directory to clean")


def main():
    """Run all backup tests."""
    print("=" * 50)
    print("BACKUP SYSTEM TEST SUITE")
    print("=" * 50)

    try:
        # Run tests
        backup_test = test_backup_service()
        csv_test = test_csv_readability()

        print("\n" + "=" * 50)
        print("TEST RESULTS")
        print("=" * 50)
        print(f"Backup Creation: {'PASS' if backup_test else 'FAIL'}")
        print(f"CSV Readability: {'PASS' if csv_test else 'FAIL'}")

        if backup_test and csv_test:
            print("\n🎉 ALL TESTS PASSED!")
            return 0
        else:
            print("\n❌ SOME TESTS FAILED!")
            return 1

    except Exception as e:
        print(f"\n💥 TEST SUITE CRASHED: {str(e)}")
        return 1

    finally:
        cleanup_test_files()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
