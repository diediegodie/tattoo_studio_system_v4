#!/usr/bin/env python3
"""
Verification script for Monthly Extrato Backup Safety Net.

This script checks all requirements for the monthly backup automation system
and provides a comprehensive status report.

Usage:
    python scripts/verify_monthly_backup_system.py
"""

import os
import sys
from datetime import datetime
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.session import SessionLocal
from app.db.base import User
from app.services.backup_service import BackupService
from app.core.config import EXTRATO_REQUIRE_BACKUP, APP_TZ


def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_check(name, status, message=""):
    """Print a check result."""
    symbol = "✓" if status else "✗"
    color = "\033[92m" if status else "\033[91m"
    reset = "\033[0m"
    print(f"{color}{symbol}{reset} {name}")
    if message:
        print(f"  → {message}")


def check_environment_variables():
    """Check required environment variables."""
    print_header("Environment Variables")

    checks = {
        "TZ": os.getenv("TZ"),
        "DATABASE_URL": os.getenv("DATABASE_URL"),
        "JWT_SECRET_KEY": os.getenv("JWT_SECRET_KEY"),
        "FLASK_SECRET_KEY": os.getenv("FLASK_SECRET_KEY"),
        "ENABLE_MONTHLY_EXTRATO_JOB": os.getenv("ENABLE_MONTHLY_EXTRATO_JOB"),
    }

    all_ok = True
    for key, value in checks.items():
        exists = value is not None and value != ""
        print_check(key, exists, f"Value: {value if exists else 'NOT SET'}")
        if not exists:
            all_ok = False

    # Check timezone
    print(f"\n  Current timezone: {APP_TZ}")
    print(f"  Recommended: America/Sao_Paulo")

    # Check backup requirement
    print(f"\n  EXTRATO_REQUIRE_BACKUP: {EXTRATO_REQUIRE_BACKUP}")
    print(f"  Recommended: True (for production)")

    return all_ok


def check_service_account():
    """Check if service account exists."""
    print_header("Service Account Status")

    try:
        with SessionLocal() as db:
            user = db.get(User, 999)

            if user:
                print_check("Service Account Exists", True, f"User ID: {user.id}")
                print(f"  Email: {user.email}")
                print(f"  Name: {user.name}")
                print(f"  Active: {user.is_active}")
                print(f"  Created: {user.created_at}")
                return True
            else:
                print_check(
                    "Service Account Exists",
                    False,
                    "Service account (user_id=999) not found",
                )
                print("\n  To create service account, restart the application.")
                print(
                    "  It will be created automatically by ensure_service_account_user()"
                )
                return False

    except Exception as e:
        print_check("Service Account Check", False, f"Error: {str(e)}")
        return False


def check_backup_directory():
    """Check if backup directory exists and is writable."""
    print_header("Backup Directory Status")

    backup_base = Path("backups")

    # Check existence
    exists = backup_base.exists()
    print_check("Backups Directory Exists", exists, f"Path: {backup_base.absolute()}")

    if not exists:
        print("\n  To create backup directory:")
        print("    mkdir -p backups")
        print("    chmod 777 backups")
        return False

    # Check if writable
    try:
        test_file = backup_base / ".write_test"
        test_file.write_text("test")
        test_file.unlink()
        print_check("Backups Directory Writable", True)
        writable = True
    except Exception as e:
        print_check("Backups Directory Writable", False, f"Error: {str(e)}")
        print("\n  To fix permissions:")
        print("    chmod -R 777 backups")
        writable = False

    # List existing backups
    if writable:
        backups = list(backup_base.glob("*/backup_*.csv"))
        print(f"\n  Existing backups: {len(backups)}")
        for backup in sorted(backups)[-5:]:  # Show last 5
            size = backup.stat().st_size
            print(f"    - {backup.name} ({size:,} bytes)")

    return exists and writable


def check_backup_service():
    """Check if backup service is working."""
    print_header("Backup Service Status")

    try:
        service = BackupService()
        print_check("Backup Service Initialized", True)

        # Try to get info for current month (won't fail if doesn't exist)
        now = datetime.now()
        info = service.get_backup_info(now.year, now.month)

        print(f"\n  Current month backup status:")
        print(f"    Month: {now.month:02d}/{now.year}")
        print(f"    Exists: {info.get('exists', False)}")
        if info.get("exists"):
            print(f"    Size: {info.get('file_size', 0):,} bytes")
            print(f"    Records: {info.get('record_count', 0)}")
            print(f"    Created: {info.get('created_at', 'N/A')}")

        return True

    except Exception as e:
        print_check("Backup Service Check", False, f"Error: {str(e)}")
        return False


def check_database_connection():
    """Check if database connection works."""
    print_header("Database Connection")

    try:
        from app.db.session import engine
        from sqlalchemy import text

        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()

        print_check("Database Connection", True, "Connection successful")

        # Check if required tables exist
        with engine.connect() as conn:
            tables = [
                "users",
                "pagamentos",
                "sessoes",
                "comissoes",
                "gastos",
                "extratos",
            ]
            for table in tables:
                try:
                    result = conn.execute(
                        text(f"SELECT COUNT(*) FROM {table} LIMIT 1")
                    )
                    count = result.fetchone()[0]
                    print_check(f"Table '{table}' exists", True, f"{count:,} records")
                except Exception as e:
                    print_check(f"Table '{table}' exists", False, str(e))

        return True

    except Exception as e:
        print_check("Database Connection", False, f"Error: {str(e)}")
        return False


def check_apscheduler_config():
    """Check APScheduler configuration in code."""
    print_header("APScheduler Configuration")

    # Read main.py to check scheduler config
    main_py = Path(__file__).parent.parent / "app" / "main.py"

    if not main_py.exists():
        print_check("main.py found", False, "File not found")
        return False

    content = main_py.read_text()

    checks = {
        "Monthly extrato job defined": "generate_monthly_extrato_job" in content,
        "CronTrigger imported": "from apscheduler.triggers.cron import CronTrigger"
        in content,
        "Job registered": 'id="monthly_extrato"' in content,
        "Schedule configured": "day=1, hour=2, minute=0" in content,
    }

    all_ok = True
    for name, status in checks.items():
        print_check(name, status)
        if not status:
            all_ok = False

    print(f"\n  Scheduler runs on: Day 1 of each month at 02:00 AM ({APP_TZ})")
    print(f"  Target: Previous month's data")
    print(f"  Enabled via: ENABLE_MONTHLY_EXTRATO_JOB environment variable")

    return all_ok


def check_github_workflow():
    """Check GitHub Actions workflow configuration."""
    print_header("GitHub Actions Workflow")

    workflow_file = (
        Path(__file__).parent.parent.parent
        / ".github"
        / "workflows"
        / "monthly_extrato_backup.yml"
    )

    if not workflow_file.exists():
        print_check("Workflow file exists", False, "File not found")
        return False

    print_check("Workflow file exists", True, str(workflow_file))

    content = workflow_file.read_text()

    # Check key configurations
    checks = {
        "Scheduled trigger": "schedule:" in content and "cron:" in content,
        "Manual trigger": "workflow_dispatch:" in content,
        "Backup endpoint": "/api/backup/create_service" in content,
        "Extrato endpoint": "/api/extrato/generate_service" in content,
        "Retry logic": "MAX_RETRIES" in content,
        "Error handling": "on failure()" in content or "failure()" in content,
    }

    all_ok = True
    for name, status in checks.items():
        print_check(name, status)
        if not status:
            all_ok = False

    print("\n  Required GitHub Secrets:")
    print("    - EXTRATO_API_BASE_URL (production API URL)")
    print("    - EXTRATO_API_TOKEN (service account JWT token)")
    print("\n  To configure secrets:")
    print("    Settings → Secrets and variables → Actions → New repository secret")

    return all_ok


def generate_jwt_token():
    """Generate a JWT token for the service account."""
    print_header("Generate Service Account JWT Token")

    try:
        from app.core.security import create_access_token
        from datetime import timedelta

        # Generate a long-lived token (10 years for automation)
        token = create_access_token(
            user_id=999,
            email="service-account@github-actions.internal",
            expires_delta=timedelta(days=3650),  # 10 years
        )

        print("✓ JWT Token generated successfully")
        print("\n" + "=" * 70)
        print("  SERVICE ACCOUNT JWT TOKEN")
        print("=" * 70)
        print(token)
        print("=" * 70)
        print("\nStore this token in GitHub Secrets as EXTRATO_API_TOKEN")
        print(
            "Settings → Secrets and variables → Actions → New repository secret\n"
        )

        return True

    except Exception as e:
        print_check("Token Generation", False, f"Error: {str(e)}")
        return False


def main():
    """Run all verification checks."""
    print("\n" + "=" * 70)
    print("  MONTHLY EXTRATO BACKUP SAFETY NET - VERIFICATION")
    print("=" * 70)
    print(f"\n  Date: {datetime.now().isoformat()}")
    print(f"  Timezone: {APP_TZ}")

    results = {
        "Environment Variables": check_environment_variables(),
        "Service Account": check_service_account(),
        "Backup Directory": check_backup_directory(),
        "Backup Service": check_backup_service(),
        "Database Connection": check_database_connection(),
        "APScheduler Config": check_apscheduler_config(),
        "GitHub Workflow": check_github_workflow(),
    }

    print_header("Summary")

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    for name, status in results.items():
        print_check(name, status)

    print(f"\n  Overall Status: {passed}/{total} checks passed")

    if passed == total:
        print("\n✓ System is ready for production!")
    else:
        print("\n✗ Some checks failed. Please address the issues above.")

    # Offer to generate token if service account exists
    if results.get("Service Account"):
        print("\n" + "-" * 70)
        response = input("\nGenerate JWT token for service account? (y/N): ")
        if response.lower() in ("y", "yes"):
            generate_jwt_token()

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
