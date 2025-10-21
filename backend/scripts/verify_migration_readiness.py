#!/usr/bin/env python3
"""
Production Migration Verification Script

This script verifies that all components are ready for the production migration
without making any database changes.

Usage:
    export [REDACTED_DATABASE_URL]
    python backend/scripts/verify_migration_readiness.py
"""

import os
import sys
import subprocess
from urllib.parse import urlparse

# Add the backend directory to the Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from sqlalchemy import text
from app.core.logging_config import get_logger
from app.db.session import get_engine

logger = get_logger(__name__)


def check_database_connection(database_url):
    """Verify database connection and check current state."""
    logger.info("Checking database connection")

    try:
        # Use centralized engine with proper pooling and observability
        engine = get_engine()
        with engine.connect() as conn:
            # Basic connection test
            version_result = conn.execute(text("SELECT version()")).fetchone()
            if version_result:
                version = version_result[0]
                logger.info(
                    "Connected", extra={"context": {"db_version": version[:50] + "..."}}
                )
            else:
                logger.error("Could not get database version")
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
                logger.error("Could not check table existence")
                return False

            table_exists = table_result[0]

            if not table_exists:
                logger.error("pagamentos table not found")
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
                logger.error("cliente_id column not found in pagamentos table")
                return False

            logger.info(
                "Current cliente_id schema",
                extra={"context": {"type": column_info[2], "nullable": column_info[1]}},
            )

            if column_info[1] == "YES":
                logger.info("cliente_id already nullable - migration not needed")
            else:
                logger.warning("cliente_id is NOT NULL - migration will be needed")

            # Count current payments
            count_result = conn.execute(
                text("SELECT COUNT(*) FROM pagamentos")
            ).fetchone()
            if count_result:
                payment_count = count_result[0]
                logger.info(
                    "Current payment count", extra={"context": {"count": payment_count}}
                )
            else:
                logger.error("Could not count payments")
                return False

            # Count payments with clients
            client_result = conn.execute(
                text("SELECT COUNT(*) FROM pagamentos WHERE cliente_id IS NOT NULL")
            ).fetchone()
            if client_result:
                with_client = client_result[0]
                logger.info(
                    "Payments with clients", extra={"context": {"count": with_client}}
                )
            else:
                logger.error("Could not count payments with clients")
                return False

            return True

    except Exception as e:
        logger.error(
            "Database connection failed",
            extra={"context": {"error": str(e)}},
            exc_info=True,
        )
        return False


def check_backup_tools():
    """Verify pg_dump is available for backup creation."""
    logger.info("Checking backup tools")

    try:
        result = subprocess.run(
            ["pg_dump", "--version"], capture_output=True, text=True
        )
        if result.returncode == 0:
            logger.info(
                "pg_dump available",
                extra={"context": {"version": result.stdout.strip()}},
            )
            return True
        else:
            logger.error("pg_dump not working properly")
            return False
    except FileNotFoundError:
        logger.error("pg_dump not found - install postgresql-client tools")
        return False


def check_migration_scripts():
    """Verify migration scripts exist and are executable."""
    logger.info("Checking migration scripts")

    scripts_dir = os.path.dirname(__file__)

    # Check production migration script
    prod_script = os.path.join(scripts_dir, "migrate_cliente_nullable_production.py")
    if os.path.exists(prod_script):
        logger.info(
            "Production migration script found",
            extra={"context": {"path": prod_script}},
        )
    else:
        logger.error(
            "Production migration script missing",
            extra={"context": {"path": prod_script}},
        )
        return False

    # Check original migration script
    orig_script = os.path.join(scripts_dir, "migrate_cliente_id_nullable.py")
    if os.path.exists(orig_script):
        logger.info(
            "Original migration script found", extra={"context": {"path": orig_script}}
        )
    else:
        logger.warning(
            "Original migration script missing",
            extra={"context": {"path": orig_script}},
        )

    # Check migration guide
    guide = os.path.join(scripts_dir, "production_migration_guide.md")
    if os.path.exists(guide):
        logger.info("Migration guide found", extra={"context": {"path": guide}})
    else:
        logger.warning("Migration guide missing", extra={"context": {"path": guide}})

    return True


def check_application_readiness():
    """Verify application code is ready for optional clients."""
    logger.info("Checking application readiness")

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
                logger.info("Pagamento model: cliente_id is nullable")
            else:
                logger.error("Pagamento model: cliente_id is still NOT NULL")
                return False
        else:
            logger.error("cliente_id field not found in Pagamento model")
            return False

    except ImportError as e:
        logger.error(
            "Could not import Pagamento model",
            extra={"context": {"error": str(e)}},
            exc_info=True,
        )
        return False

    # Check if controller is updated
    try:
        # This is a basic check - in production you might want more thorough verification
        controller_file = os.path.join(
            backend_dir, "app", "controllers", "financeiro_controller.py"
        )
        if os.path.exists(controller_file):
            logger.info("financeiro_controller.py exists")
        else:
            logger.error("financeiro_controller.py not found")
            return False
    except Exception as e:
        logger.error(
            "Controller check failed",
            extra={"context": {"error": str(e)}},
            exc_info=True,
        )
        return False

    return True


def main():
    logger.info(
        "Production Migration Readiness Check",
        extra={"context": {"delimiter": "=" * 50}},
    )

    # Get database URL
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        logger.error("DATABASE_URL environment variable not set")
        logger.info(
            "Export your production database URL first",
            extra={
                "context": {
                    "example": "export DATABASE_URL='postgresql://user:password@host:port/dbname'"
                }
            },
        )
        return 1

    # Parse URL to hide password in output
    parsed = urlparse(database_url)
    safe_url = f"{parsed.scheme}://{parsed.username}@{parsed.hostname}:{parsed.port or 5432}/{parsed.path[1:]}"
    logger.info("Target database", extra={"context": {"url": safe_url}})

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
    logger.info(
        "Readiness Summary",
        extra={"context": {"passed": checks_passed, "total": total_checks}},
    )

    if checks_passed == total_checks:
        logger.info("All checks passed! Ready for production migration.")
        logger.info(
            "Next steps",
            extra={
                "context": {
                    "steps": [
                        "Review the migration guide: backend/scripts/production_migration_guide.md",
                        "Schedule maintenance window",
                        "Run: python backend/scripts/migrate_cliente_nullable_production.py",
                    ]
                }
            },
        )
        return 0
    else:
        logger.error(
            "Some checks failed. Address issues before proceeding with migration."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
