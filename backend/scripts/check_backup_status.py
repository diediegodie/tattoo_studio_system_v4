#!/usr/bin/env python3
"""
Check backup status before running extrato generation.

This script verifies that a backup exists for a given month/year
and provides actionable feedback.

Usage:
    python backend/scripts/check_backup_status.py --month 10 --year 2025
    python backend/scripts/check_backup_status.py  # Checks previous month
"""

import argparse
import os
import sys
from pathlib import Path

# Add backend to path
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from dotenv import load_dotenv

# Load environment variables
env_file = backend_root.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

from app.services.backup_service import BackupService
from app.core.config import EXTRATO_REQUIRE_BACKUP


from typing import Optional


def check_backup(month: Optional[int] = None, year: Optional[int] = None):
    """Check if backup exists for specified month/year."""

    # If not specified, check previous month
    if month is None or year is None:
        from app.services.extrato_core import get_previous_month

        month, year = get_previous_month()

    print("=" * 80)
    print("🔍 Backup Status Check")
    print("=" * 80)
    print()
    print(f"📅 Target: {month:02d}/{year}")
    print(
        f"🔒 Backup Requirement: {'REQUIRED' if EXTRATO_REQUIRE_BACKUP else 'OPTIONAL'}"
    )
    print(f"   (EXTRATO_REQUIRE_BACKUP={os.getenv('EXTRATO_REQUIRE_BACKUP', 'true')})")
    print()

    # Check backup
    backup_service = BackupService()
    backup_exists = backup_service.verify_backup_exists(year, month)

    if backup_exists:
        print("✅ Backup Status: EXISTS")
        print()

        # Get backup info
        info = backup_service.get_backup_info(year, month)
        print("📊 Backup Details:")
        print(f"   Path: {info.get('file_path', 'N/A')}")
        print(f"   Size: {info.get('file_size', 0):,} bytes")
        print(f"   Records: {info.get('record_count', 0):,}")
        print(f"   Created: {info.get('created_at', 'N/A')}")
        print()
        print("✅ READY: Extrato generation can proceed")
        print()
        return 0
    else:
        print("❌ Backup Status: MISSING")
        print()

        # Get expected path
        info = backup_service.get_backup_info(year, month)
        print("❌ Expected Path:")
        print(f"   {info.get('file_path', 'N/A')}")
        print()

        if EXTRATO_REQUIRE_BACKUP:
            print("🚫 ACTION REQUIRED:")
            print()
            print("   Backup is REQUIRED (EXTRATO_REQUIRE_BACKUP=true)")
            print("   Extrato generation will FAIL without a backup.")
            print()
            print("   Options:")
            print("   1. Create a backup first:")
            print(
                f"      python backend/scripts/create_backup.py --month {month} --year {year}"
            )
            print()
            print("   2. Disable backup requirement (not recommended for production):")
            print("      Set environment variable: EXTRATO_REQUIRE_BACKUP=false")
            print()
            return 1
        else:
            print("⚠️  WARNING:")
            print()
            print("   Backup is OPTIONAL (EXTRATO_REQUIRE_BACKUP=false)")
            print("   Extrato generation will proceed WITHOUT backup.")
            print("   This is NOT recommended for production with real data.")
            print()
            print("   Recommendation:")
            print(
                f"      python backend/scripts/create_backup.py --month {month} --year {year}"
            )
            print()
            return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check backup status for extrato generation"
    )
    parser.add_argument("--month", type=int, help="Month (1-12)")
    parser.add_argument("--year", type=int, help="Year (YYYY)")

    args = parser.parse_args()

    try:
        exit_code = check_backup(args.month, args.year)
        sys.exit(exit_code)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
