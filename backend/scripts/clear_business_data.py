#!/usr/bin/env python3
"""
Database cleanup script for Tattoo Studio Management System.

This script clears all business data from the database while keeping the schema intact.
It preserves system tables (users, oauth) for authentication.

Usage:
    python scripts/clear_business_data.py
"""

import os
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.logging_config import get_logger

logger = get_logger(__name__)


def clear_business_data():
    """Clear all business data from the database."""
    logger.info("Clearing business data from database...")

    # Detect environment and set up database connection
    if os.path.exists("/.dockerenv") or os.getenv("DOCKER_RESET") == "1":
        # Docker environment - use PostgreSQL
        logger.info("Detected Docker environment, using PostgreSQL...")
        db_url = os.getenv(
            "DATABASE_URL", "[REDACTED_DATABASE_URL]"
        )
        os.environ["DATABASE_URL"] = db_url
    else:
        # Local environment - use SQLite
        logger.info("Detected local environment, using SQLite...")
        local_db_path = backend_dir.parent / "tattoo_studio_dev.db"
        db_url = f"sqlite:///{local_db_path}"
        os.environ["DATABASE_URL"] = db_url

    try:
        from app.db.session import SessionLocal, engine
        from sqlalchemy import text

        # Business tables to clear (in reverse dependency order)
        business_tables = [
            "extrato_snapshots",
            "extrato_run_logs",
            "extratos",
            "comissoes",
            "pagamentos",
            "sessoes",
            "gastos",
            "inventory",
            "clients",
        ]

        # System tables to preserve
        system_tables = ["users", "oauth"]

        logger.info(
            "Will clear business tables",
            extra={"context": {"count": len(business_tables)}},
        )
        logger.info(
            "Will preserve system tables", extra={"context": {"tables": system_tables}}
        )

        # Clear business data
        with engine.connect() as conn:
            for table in business_tables:
                try:
                    if "postgresql" in db_url:
                        # PostgreSQL - use TRUNCATE CASCADE
                        cmd = f"TRUNCATE TABLE {table} CASCADE;"
                    else:
                        # SQLite - use DELETE
                        cmd = f"DELETE FROM {table};"

                    logger.info("Clearing table", extra={"context": {"table": table}})
                    conn.execute(text(cmd))
                    conn.commit()
                except Exception as e:
                    logger.warning(
                        "Error clearing table",
                        extra={"context": {"table": table, "error": str(e)}},
                    )
                    conn.rollback()

        # Verify tables are empty
        logger.info("Verifying tables are empty...")
        with engine.connect() as conn:
            for table in business_tables:
                try:
                    result = conn.execute(
                        text(f"SELECT COUNT(*) as count FROM {table}")
                    )
                    count = result.fetchone()[0]
                    if count == 0:
                        logger.info(
                            "Table empty",
                            extra={"context": {"table": table, "rows": count}},
                        )
                    else:
                        logger.warning(
                            "Table not empty",
                            extra={"context": {"table": table, "rows": count}},
                        )
                except Exception as e:
                    logger.error(
                        "Error checking table",
                        extra={"context": {"table": table, "error": str(e)}},
                    )

        logger.info(
            "Business data cleared successfully! Schema remains intact - you can now create fresh test data manually"
        )

    except Exception as e:
        logger.error(
            "Database cleanup failed",
            extra={"context": {"error": str(e)}},
            exc_info=True,
        )
        return False

    return True


if __name__ == "__main__":
    success = clear_business_data()
    sys.exit(0 if success else 1)
