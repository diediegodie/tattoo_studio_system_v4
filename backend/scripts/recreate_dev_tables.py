#!/usr/bin/env python3
"""
SQLite Migration Script: Recreate tables with nullable cliente_id

This script recreates all tables with the current model schema,
which includes nullable=True for cliente_id in pagamentos table.

WARNING: This will DELETE ALL DATA! Only use for development.
"""

import os
import sys
import shutil
from datetime import datetime

# Add the backend directory to the Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from app.db.session import engine
from app.db.base import Base
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def recreate_tables_with_nullable_cliente_id():
    """Recreate all tables with current schema (nullable cliente_id)."""

    # Create backup of current database
    db_path = "tattoo_studio_dev.db"
    if os.path.exists(db_path):
        backup_path = (
            f"tattoo_studio_dev_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        )
        shutil.copy2(db_path, backup_path)
        logger.info("Created backup", extra={"context": {"path": backup_path}})
    else:
        backup_path = None
        logger.warning(
            "Database file not found for backup", extra={"context": {"path": db_path}}
        )

    try:
        # Drop all existing tables
        Base.metadata.drop_all(engine)
        logger.info("Dropped all existing tables")

        # Create all tables with new schema
        Base.metadata.create_all(engine)
        logger.info(
            "Created all tables with new schema",
            extra={"context": {"change": "cliente_id nullable"}},
        )

        logger.info("Migration completed successfully")
        logger.warning("All data has been lost. Development-only operation.")

        return True

    except Exception as e:
        logger.error(
            "Error during migration",
            extra={"context": {"error": str(e)}},
            exc_info=True,
        )
        if backup_path and os.path.exists(backup_path):
            logger.info("Backup available", extra={"context": {"path": backup_path}})
        return False


if __name__ == "__main__":
    logger.warning("This will DELETE ALL DATA in the database! Development only.")
    response = input("Continue? (yes/no): ").lower().strip()
    if response == "yes":
        recreate_tables_with_nullable_cliente_id()
    else:
        logger.info("Migration cancelled by user")
