#!/usr/bin/env python3
"""
Production Migration Verification Script

This script verifies that all components are ready for the production migration
without making any database changes.

Usage:
    export DATABASE_URL="postgresql://user:password@host:port/database"
    python backend/scripts/verify_migration_readiness.py
"""

import os
import sys
import subprocess
from urllib.parse import urlparse

# Add the backend directory to the Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from sqlalchemy import text, create_engine


def check_database_connection(database_url):
    """Verify database connection and check current state."""
    print("🔍 Checking database connection...")

    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            # Basic connection test
            version_result = conn.execute(text("SELECT version()")).fetchone()
            if version_result:
                version = version_result[0]
                print(f"✅ Connected to: {version[:50]}...")
            else:
                print("❌ Could not get database version")
                return False

            # Check pagamentos table exists
            table_result = conn.execute(
                text(
                    """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'pagamentos'
                );
            """
                )
            ).fetchone()

            if not table_result:
                print("❌ Could not check table existence")
                return False

            table_exists = table_result[0]

            if not table_exists:
                print("❌ pagamentos table not found")
                return False

            # Check current schema
            column_info = conn.execute(
                text(
                    """
                SELECT column_name, is_nullable, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'pagamentos' AND column_name = 'cliente_id';
            """
                )
            ).fetchone()

            if not column_info:
                print("❌ cliente_id column not found in pagamentos table")
                return False

            print(
                f"📊 Current cliente_id schema: {column_info[2]}, nullable: {column_info[1]}"
            )

            if column_info[1] == "YES":
                print("ℹ️  cliente_id is already nullable - migration not needed")
            else:
                print("📝 cliente_id is NOT NULL - migration will be needed")

            # Count current payments
            count_result = conn.execute(
                text("SELECT COUNT(*) FROM pagamentos")
            ).fetchone()
            if count_result:
                payment_count = count_result[0]
                print(f"📈 Current payment count: {payment_count}")
            else:
                print("❌ Could not count payments")
                return False

            # Count payments with clients
            client_result = conn.execute(
                text("SELECT COUNT(*) FROM pagamentos WHERE cliente_id IS NOT NULL")
            ).fetchone()
            if client_result:
                with_client = client_result[0]
                print(f"👥 Payments with clients: {with_client}")
            else:
                print("❌ Could not count payments with clients")
                return False

            return True

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False


def check_backup_tools():
    """Verify pg_dump is available for backup creation."""
    print("\n🛠️  Checking backup tools...")

    try:
        result = subprocess.run(
            ["pg_dump", "--version"], capture_output=True, text=True
        )
        if result.returncode == 0:
            print(f"✅ pg_dump available: {result.stdout.strip()}")
            return True
        else:
            print("❌ pg_dump not working properly")
            return False
    except FileNotFoundError:
        print("❌ pg_dump not found - install postgresql-client tools")
        return False


def check_migration_scripts():
    """Verify migration scripts exist and are executable."""
    print("\n📁 Checking migration scripts...")

    scripts_dir = os.path.dirname(__file__)

    # Check production migration script
    prod_script = os.path.join(scripts_dir, "migrate_cliente_nullable_production.py")
    if os.path.exists(prod_script):
        print(f"✅ Production migration script found: {prod_script}")
    else:
        print(f"❌ Production migration script missing: {prod_script}")
        return False

    # Check original migration script
    orig_script = os.path.join(scripts_dir, "migrate_cliente_id_nullable.py")
    if os.path.exists(orig_script):
        print(f"✅ Original migration script found: {orig_script}")
    else:
        print(f"❌ Original migration script missing: {orig_script}")

    # Check migration guide
    guide = os.path.join(scripts_dir, "production_migration_guide.md")
    if os.path.exists(guide):
        print(f"✅ Migration guide found: {guide}")
    else:
        print(f"❌ Migration guide missing: {guide}")

    return True


def check_application_readiness():
    """Verify application code is ready for optional clients."""
    print("\n🖥️  Checking application readiness...")

    # Check if model is updated
    try:
        from app.db.base import Pagamento

        # Check if cliente_id field is nullable
        cliente_id_field = None
        for column in Pagamento.__table__.columns:
            if column.name == "cliente_id":
                cliente_id_field = column
                break

        if cliente_id_field is not None:
            if (
                hasattr(cliente_id_field, "nullable")
                and cliente_id_field.nullable is True
            ):
                print("✅ Pagamento model: cliente_id is nullable")
            else:
                print("❌ Pagamento model: cliente_id is still NOT NULL")
                return False
        else:
            print("❌ cliente_id field not found in Pagamento model")
            return False

    except ImportError as e:
        print(f"❌ Could not import Pagamento model: {e}")
        return False

    # Check if controller is updated
    try:
        # This is a basic check - in production you might want more thorough verification
        controller_file = os.path.join(
            backend_dir, "app", "controllers", "financeiro_controller.py"
        )
        if os.path.exists(controller_file):
            print("✅ financeiro_controller.py exists")
        else:
            print("❌ financeiro_controller.py not found")
            return False
    except Exception as e:
        print(f"❌ Controller check failed: {e}")
        return False

    return True


def main():
    print("🔍 Production Migration Readiness Check")
    print("=" * 50)

    # Get database URL
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        print("   Export your production database URL first:")
        print("   export DATABASE_URL='postgresql://user:password@host:port/database'")
        return 1

    # Parse URL to hide password in output
    parsed = urlparse(database_url)
    safe_url = f"{parsed.scheme}://{parsed.username}@{parsed.hostname}:{parsed.port or 5432}/{parsed.path[1:]}"
    print(f"🎯 Target database: {safe_url}")

    checks_passed = 0
    total_checks = 4

    # Run all checks
    if check_database_connection(database_url):
        checks_passed += 1

    if check_backup_tools():
        checks_passed += 1

    if check_migration_scripts():
        checks_passed += 1

    if check_application_readiness():
        checks_passed += 1

    # Summary
    print("\n" + "=" * 50)
    print(f"📊 Readiness Summary: {checks_passed}/{total_checks} checks passed")

    if checks_passed == total_checks:
        print("🎉 All checks passed! Ready for production migration.")
        print("\nNext steps:")
        print(
            "1. Review the migration guide: backend/scripts/production_migration_guide.md"
        )
        print("2. Schedule maintenance window")
        print("3. Run: python backend/scripts/migrate_cliente_nullable_production.py")
        return 0
    else:
        print("❌ Some checks failed. Address issues before proceeding with migration.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
