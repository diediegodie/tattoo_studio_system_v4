"""
Migration script to add google_event_id column to sessoes table.
Run this script to update existing databases.

Usage:
    python -m backend.scripts.add_google_event_id_column
"""

import logging
import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def add_google_event_id_column():
    """Add google_event_id column to sessoes table if it doesn't exist."""
    try:
        # Get database URL from environment or use default
        database_url = os.environ.get("DATABASE_URL", "sqlite:///app.db")

        # Create engine
        engine = create_engine(database_url)

        # Check if column already exists
        with engine.connect() as conn:
            # For SQLite, use PRAGMA table_info
            if "sqlite" in database_url:
                result = conn.execute(text("PRAGMA table_info(sessoes)")).fetchall()
                column_exists = any(col[1] == "google_event_id" for col in result)
            else:
                # For PostgreSQL, use information_schema
                result = conn.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = 'sessoes' AND column_name = 'google_event_id'"
                    )
                ).fetchone()
                column_exists = bool(result)

            # Add the column if it doesn't exist
            if not column_exists:
                logger.info("Adding google_event_id column to sessoes table...")

                # Different SQL for different databases
                if "sqlite" in database_url:
                    conn.execute(
                        text(
                            "ALTER TABLE sessoes ADD COLUMN google_event_id VARCHAR(100) UNIQUE"
                        )
                    )
                else:
                    conn.execute(
                        text(
                            "ALTER TABLE sessoes ADD COLUMN google_event_id VARCHAR(100) UNIQUE"
                        )
                    )

                conn.commit()
                logger.info("Column added successfully!")
            else:
                logger.info("Column google_event_id already exists in sessoes table.")

        return True

    except SQLAlchemyError as e:
        logger.error(f"Database error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return False


if __name__ == "__main__":
    logger.info("Starting database migration...")
    success = add_google_event_id_column()

    if success:
        logger.info("Migration completed successfully!")
        sys.exit(0)
    else:
        logger.error("Migration failed!")
        sys.exit(1)
