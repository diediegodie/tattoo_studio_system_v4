"""
Database migration functions.

This module contains functions that apply schema migrations automatically
during application startup. Each migration function is idempotent and safe
to run multiple times.
"""

import logging
from sqlalchemy import text, inspect
from app.db.session import get_engine

logger = logging.getLogger(__name__)


def ensure_migration_001_applied() -> None:
    """
    Migration 001: Make jotform_submission_id nullable in clients table.

    This migration allows manual client creation without requiring a JotForm
    submission. It checks if the migration is needed and applies it only once.

    This function is idempotent - it can be called multiple times safely.
    - If already applied, it does nothing
    - If needed, it applies the migration
    - Works with both SQLite and PostgreSQL
    """
    try:
        engine = get_engine()
        dialect_name = engine.dialect.name

        with engine.connect() as conn:
            # Check if migration is needed
            inspector = inspect(engine)
            columns = inspector.get_columns("clients")

            # Find jotform_submission_id column
            jotform_col = None
            for col in columns:
                if col["name"] == "jotform_submission_id":
                    jotform_col = col
                    break

            if not jotform_col:
                logger.warning(
                    "Migration 001 skipped - jotform_submission_id column not found",
                    extra={"context": {"table": "clients"}},
                )
                return

            # Check if already nullable
            is_nullable = jotform_col.get("nullable", False)

            if is_nullable:
                logger.debug(
                    "Migration 001 already applied - jotform_submission_id is nullable",
                    extra={
                        "context": {
                            "table": "clients",
                            "column": "jotform_submission_id",
                        }
                    },
                )
                return

            # Apply migration based on database type
            logger.info(
                "Applying Migration 001 - making jotform_submission_id nullable",
                extra={"context": {"dialect": dialect_name, "table": "clients"}},
            )

            if dialect_name == "postgresql":
                # PostgreSQL: Simple ALTER COLUMN
                conn.execute(
                    text(
                        """
                    ALTER TABLE clients 
                    ALTER COLUMN jotform_submission_id DROP NOT NULL;
                """
                    )
                )
                conn.commit()

            elif dialect_name == "sqlite":
                # SQLite: Must recreate table (SQLite limitation)
                # Step 1: Create new table with nullable column
                conn.execute(
                    text(
                        """
                    CREATE TABLE clients_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(255) NOT NULL,
                        jotform_submission_id VARCHAR(100) UNIQUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP
                    );
                """
                    )
                )

                # Step 2: Copy data
                conn.execute(
                    text(
                        """
                    INSERT INTO clients_new (id, name, jotform_submission_id, created_at, updated_at)
                    SELECT id, name, jotform_submission_id, created_at, updated_at
                    FROM clients;
                """
                    )
                )

                # Step 3: Drop old table
                conn.execute(text("DROP TABLE clients;"))

                # Step 4: Rename new table
                conn.execute(text("ALTER TABLE clients_new RENAME TO clients;"))

                conn.commit()
            else:
                logger.warning(
                    "Migration 001 skipped - unsupported database dialect",
                    extra={"context": {"dialect": dialect_name}},
                )
                return

            logger.info(
                "Migration 001 applied successfully",
                extra={
                    "context": {
                        "dialect": dialect_name,
                        "table": "clients",
                        "column": "jotform_submission_id",
                        "change": "NOT NULL -> NULL",
                    }
                },
            )

    except Exception as e:
        logger.error(
            "Failed to apply Migration 001",
            extra={"context": {"error": str(e)}},
            exc_info=True,
        )
        # Don't raise - app should still start even if migration fails
        # Existing Jotform clients will still work, only manual input will fail
