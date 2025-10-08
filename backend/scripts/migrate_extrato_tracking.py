#!/usr/bin/env python3
"""
Database migration script to add ExtratoRunLog table.
Run this script to create the new table for tracking extrato generation runs.
"""

import os
import sys

from sqlalchemy import create_engine, text

# Add the backend directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.logging_config import get_logger
from app.db.base import Base
from app.db.session import engine

logger = get_logger(__name__)


def create_extrato_run_log_table():
    """Create the extrato_run_logs table if it doesn't exist."""

    # SQL to create the table
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS extrato_run_logs (
        id SERIAL PRIMARY KEY,
        mes INTEGER NOT NULL,
        ano INTEGER NOT NULL,
        run_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
        status VARCHAR(50) NOT NULL,
        message VARCHAR(500),
        CONSTRAINT unique_extrato_run_per_month UNIQUE (mes, ano, status)
    );
    """

    try:
        with engine.connect() as conn:
            conn.execute(text(create_table_sql))
            conn.commit()
            logger.info("ExtratoRunLog table created successfully!")
    except Exception as e:
        logger.error(f"Error creating table: {e}")
        return False

    return True


def main():
    logger.info("Starting database migration for ExtratoRunLog table...")

    if create_extrato_run_log_table():
        logger.info("Migration completed successfully!")
        logger.info(
            "The extrato system now uses database-based tracking instead of file-based."
        )
    else:
        logger.error("Migration failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
