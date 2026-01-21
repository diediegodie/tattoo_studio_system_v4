#!/usr/bin/env python3
"""
Drop hora column from sessoes table

This migration removes the unused hora column from the sessoes table.
The column was replaced with created_at timestamp tracking.

Usage:
    python drop_hora_column.py
"""

import os
import sys
from datetime import datetime
import logging

# Add parent directories to path so we can import app modules
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.insert(0, backend_dir)

from app import create_app
from app.core.logging_config import get_logger
from app.db.session import SessionLocal
from sqlalchemy import text


def check_column_exists(db_session, logger):
    """Check if hora column exists in sessoes table."""
    try:
        # Check if hora column exists first (PostgreSQL way)
        # This function is called from drop_hora_column, no need to duplicate check here
        pass

        # If SQLite pragma doesn't work, try PostgreSQL approach
        try:
            result = db_session.execute(text("""
                SELECT COUNT(*) as count
                FROM information_schema.columns 
                WHERE table_name = 'sessoes' AND column_name = 'hora'
            """)).fetchone()
            return result and result[0] > 0
        except Exception:
            # If both fail, assume column exists to be safe
            logger.warning(
                "Could not determine if hora column exists, assuming it does"
            )
            return True

    except Exception as e:
        logger.warning(f"Error checking column existence: {e}")
        return True


def drop_hora_column(db_session, logger):
    """Drop the hora column from sessoes table."""
    try:
        # First check if column exists
        if not check_column_exists(db_session, logger):
            logger.info("hora column does not exist, migration already completed")
            return True

        logger.info("Dropping hora column from sessoes table...")

        # For SQLite, we need to recreate the table without the hora column
        # For PostgreSQL, we can use ALTER TABLE DROP COLUMN
        try:
            # Try PostgreSQL approach first
            db_session.execute(text("ALTER TABLE sessoes DROP COLUMN IF EXISTS hora"))
            db_session.commit()
            logger.info("Successfully dropped hora column using ALTER TABLE")
            return True

        except Exception as pg_error:
            logger.info(f"PostgreSQL ALTER TABLE failed: {pg_error}")
            logger.info("Attempting SQLite approach...")
            db_session.rollback()

            # SQLite approach - recreate table without hora column
            # Drop temporary table if it exists
            db_session.execute(text("DROP TABLE IF EXISTS sessoes_new"))

            db_session.execute(text("""
                CREATE TABLE sessoes_new (
                    id SERIAL PRIMARY KEY,
                    data DATE NOT NULL,
                    cliente_id INTEGER NOT NULL,
                    artista_id INTEGER NOT NULL,
                    valor NUMERIC(10,2) NOT NULL,
                    observacoes VARCHAR(255),
                    google_event_id VARCHAR(100),
                    status VARCHAR(20) DEFAULT 'active',
                    payment_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (cliente_id) REFERENCES clientes (id),
                    FOREIGN KEY (artista_id) REFERENCES artistas (id)
                )
            """))

            # Copy data from old table to new table (excluding hora)
            db_session.execute(text("""
                INSERT INTO sessoes_new (
                    id, data, cliente_id, artista_id, valor, observacoes, 
                    google_event_id, status, payment_id, created_at, updated_at
                )
                SELECT 
                    id, data, cliente_id, artista_id, valor, observacoes,
                    google_event_id, status, payment_id, created_at, updated_at
                FROM sessoes
            """))

            # Drop old table and rename new table
            db_session.execute(text("DROP TABLE sessoes"))
            db_session.execute(text("ALTER TABLE sessoes_new RENAME TO sessoes"))

            db_session.commit()
            logger.info("Successfully dropped hora column using table recreation")
            return True

    except Exception as e:
        logger.error(f"Error dropping hora column: {e}")
        db_session.rollback()
        return False


def main():
    """Main migration function."""
    logger = get_logger(__name__)
    logger.info("Starting hora column drop migration...")

    try:
        # Create app and get database session
        app = create_app()

        with app.app_context():
            db_session = SessionLocal()

            try:
                success = drop_hora_column(db_session, logger)

                if success:
                    logger.info("Migration completed successfully!")
                    logger.info(
                        "The hora column has been dropped from the sessoes table"
                    )
                    return 0
                else:
                    logger.error("Migration failed!")
                    return 1

            finally:
                db_session.close()

    except Exception as e:
        logger.error(f"Migration failed with error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
