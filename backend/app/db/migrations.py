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
                conn.execute(text("""
                    ALTER TABLE clients 
                    ALTER COLUMN jotform_submission_id DROP NOT NULL;
                """))
                conn.commit()

            elif dialect_name == "sqlite":
                # SQLite: Must recreate table (SQLite limitation)
                # Step 1: Create new table with nullable column
                conn.execute(text("""
                    CREATE TABLE clients_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name VARCHAR(255) NOT NULL,
                        jotform_submission_id VARCHAR(100) UNIQUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP
                    );
                """))

                # Step 2: Copy data
                conn.execute(text("""
                    INSERT INTO clients_new (id, name, jotform_submission_id, created_at, updated_at)
                    SELECT id, name, jotform_submission_id, created_at, updated_at
                    FROM clients;
                """))

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


def ensure_migration_002_applied() -> None:
    """
    Migration 002: Create migration_audit table.

    This migration creates an audit trail table for tracking migration operations
    during the sessions/payments unification refactoring (Phase 1).

    Privacy: Contains ONLY IDs and technical metadata - NO PII.
    Retention: 90 days post-stable deployment (or per compliance requirements).

    This function is idempotent - safe to call multiple times.
    """
    try:
        engine = get_engine()
        dialect_name = engine.dialect.name

        with engine.connect() as conn:
            # Check if table already exists
            inspector = inspect(engine)
            tables = inspector.get_table_names()

            if "migration_audit" in tables:
                logger.debug(
                    "Migration 002 already applied - migration_audit table exists",
                    extra={"context": {"table": "migration_audit"}},
                )
                return

            logger.info(
                "Applying Migration 002 - creating migration_audit table",
                extra={"context": {"dialect": dialect_name}},
            )

            if dialect_name == "postgresql":
                conn.execute(text("""
                    CREATE TABLE migration_audit (
                        id SERIAL PRIMARY KEY,
                        entity_type VARCHAR(50) NOT NULL,
                        entity_id INTEGER,
                        action VARCHAR(50) NOT NULL,
                        status VARCHAR(20) NOT NULL,
                        details JSONB,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                    );
                    CREATE INDEX idx_migration_audit_entity_type ON migration_audit(entity_type);
                    CREATE INDEX idx_migration_audit_created_at ON migration_audit(created_at);
                """))
                conn.commit()

            elif dialect_name == "sqlite":
                conn.execute(text("""
                    CREATE TABLE migration_audit (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        entity_type VARCHAR(50) NOT NULL,
                        entity_id INTEGER,
                        action VARCHAR(50) NOT NULL,
                        status VARCHAR(20) NOT NULL,
                        details TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """))
                conn.execute(
                    text(
                        "CREATE INDEX idx_migration_audit_entity_type ON migration_audit(entity_type);"
                    )
                )
                conn.execute(
                    text(
                        "CREATE INDEX idx_migration_audit_created_at ON migration_audit(created_at);"
                    )
                )
                conn.commit()

            else:
                logger.warning(
                    "Migration 002 skipped - unsupported database dialect",
                    extra={"context": {"dialect": dialect_name}},
                )
                return

            logger.info(
                "Migration 002 applied successfully",
                extra={
                    "context": {
                        "dialect": dialect_name,
                        "table": "migration_audit",
                        "action": "created",
                    }
                },
            )

    except Exception as e:
        logger.error(
            "Failed to apply Migration 002",
            extra={"context": {"error": str(e)}},
            exc_info=True,
        )
        # Don't raise - app should still start


def ensure_migration_003_applied() -> None:
    """
    Migration 003: Add google_event_id column to pagamentos table.

    This migration adds the google_event_id column with a UNIQUE constraint
    to prevent duplicate payment creation from the same Google Calendar event.

    Column spec: google_event_id VARCHAR(100) UNIQUE NULL
    Purpose: Duplicate prevention in unified session+payment flow (Phase 1)

    This function is idempotent - safe to call multiple times.
    """
    try:
        engine = get_engine()
        dialect_name = engine.dialect.name

        with engine.connect() as conn:
            # Check if column already exists
            inspector = inspect(engine)
            columns = inspector.get_columns("pagamentos")

            google_event_col = None
            for col in columns:
                if col["name"] == "google_event_id":
                    google_event_col = col
                    break

            if google_event_col:
                logger.debug(
                    "Migration 003 already applied - google_event_id column exists",
                    extra={
                        "context": {"table": "pagamentos", "column": "google_event_id"}
                    },
                )
                return

            logger.info(
                "Applying Migration 003 - adding google_event_id to pagamentos",
                extra={"context": {"dialect": dialect_name, "table": "pagamentos"}},
            )

            if dialect_name == "postgresql":
                # PostgreSQL: Simple ALTER TABLE
                conn.execute(text("""
                    ALTER TABLE pagamentos 
                    ADD COLUMN google_event_id VARCHAR(100) NULL;
                """))
                # Add unique constraint (partial - only for non-NULL values)
                conn.execute(text("""
                    CREATE UNIQUE INDEX idx_pagamentos_google_event_id 
                    ON pagamentos(google_event_id) 
                    WHERE google_event_id IS NOT NULL;
                """))
                conn.commit()

            elif dialect_name == "sqlite":
                # SQLite: ALTER TABLE ADD COLUMN is supported
                conn.execute(text("""
                    ALTER TABLE pagamentos 
                    ADD COLUMN google_event_id VARCHAR(100) NULL;
                """))
                # SQLite unique index (conditional on NULL requires WHERE clause)
                conn.execute(text("""
                    CREATE UNIQUE INDEX idx_pagamentos_google_event_id 
                    ON pagamentos(google_event_id) 
                    WHERE google_event_id IS NOT NULL;
                """))
                conn.commit()

            else:
                logger.warning(
                    "Migration 003 skipped - unsupported database dialect",
                    extra={"context": {"dialect": dialect_name}},
                )
                return

            logger.info(
                "Migration 003 applied successfully",
                extra={
                    "context": {
                        "dialect": dialect_name,
                        "table": "pagamentos",
                        "column": "google_event_id",
                        "constraint": "UNIQUE",
                    }
                },
            )

    except Exception as e:
        logger.error(
            "Failed to apply Migration 003",
            extra={"context": {"error": str(e)}},
            exc_info=True,
        )
        # Don't raise - app should still start


def ensure_migration_004_backfill_google_event_id() -> None:
    """
    Migration 004: Backfill google_event_id from sessoes to pagamentos.

    This migration populates google_event_id in existing pagamentos by joining
    with sessoes where a link exists (via sessao_id or payment_id).

    Collision handling: If multiple pagamentos link to sessoes with the same
    google_event_id, skip the assignment and log to migration_audit with
    status='collision'.

    Idempotency: Only assigns if google_event_id IS NULL. Safe to re-run.

    This function is idempotent - safe to call multiple times.
    """
    try:
        engine = get_engine()
        dialect_name = engine.dialect.name

        with engine.connect() as conn:
            # Check if migration_audit table exists (dependency)
            inspector = inspect(engine)
            tables = inspector.get_table_names()

            if "migration_audit" not in tables:
                logger.warning(
                    "Migration 004 skipped - migration_audit table not found (run Migration 002 first)",
                    extra={"context": {"dependency": "migration_audit"}},
                )
                return

            # Check if google_event_id column exists in pagamentos
            columns = inspector.get_columns("pagamentos")
            has_google_event_id = any(
                col["name"] == "google_event_id" for col in columns
            )

            if not has_google_event_id:
                logger.warning(
                    "Migration 004 skipped - google_event_id column not found in pagamentos (run Migration 003 first)",
                    extra={
                        "context": {"table": "pagamentos", "column": "google_event_id"}
                    },
                )
                return

            logger.info(
                "Applying Migration 004 - backfilling google_event_id",
                extra={"context": {"dialect": dialect_name}},
            )

            # Step 1: Find collision candidates (same google_event_id linked to multiple pagamentos)
            collision_query = text("""
                SELECT s.google_event_id, COUNT(DISTINCT p.id) as pagamento_count
                FROM sessoes s
                INNER JOIN pagamentos p ON (p.sessao_id = s.id OR s.payment_id = p.id)
                WHERE s.google_event_id IS NOT NULL
                  AND p.google_event_id IS NULL
                GROUP BY s.google_event_id
                HAVING COUNT(DISTINCT p.id) > 1
            """)
            collision_result = conn.execute(collision_query).fetchall()
            collision_event_ids = {row[0] for row in collision_result}

            # Log collisions to migration_audit
            for event_id in collision_event_ids:
                conn.execute(
                    text("""
                    INSERT INTO migration_audit (entity_type, entity_id, action, status, details)
                    VALUES (:entity_type, NULL, :action, :status, :details)
                """),
                    {
                        "entity_type": "pagamento_backfill",
                        "action": "backfill",
                        "status": "collision",
                        "details": f'{{"google_event_id": "{event_id}", "reason": "multiple_pagamentos_for_same_event"}}',
                    },
                )

            # Step 2: Backfill where no collision detected
            if dialect_name == "postgresql":
                backfill_query = text("""
                    UPDATE pagamentos p
                    SET google_event_id = s.google_event_id
                    FROM sessoes s
                    WHERE (p.sessao_id = s.id OR s.payment_id = p.id)
                      AND s.google_event_id IS NOT NULL
                      AND p.google_event_id IS NULL
                      AND s.google_event_id NOT IN :collision_ids
                """)
                result = conn.execute(
                    backfill_query,
                    {
                        "collision_ids": (
                            tuple(collision_event_ids) if collision_event_ids else ("",)
                        )
                    },
                )
                rows_updated = result.rowcount

            elif dialect_name == "sqlite":
                # SQLite doesn't support UPDATE FROM, use subquery
                backfill_query = text("""
                    UPDATE pagamentos
                    SET google_event_id = (
                        SELECT s.google_event_id
                        FROM sessoes s
                        WHERE (pagamentos.sessao_id = s.id OR s.payment_id = pagamentos.id)
                          AND s.google_event_id IS NOT NULL
                        LIMIT 1
                    )
                    WHERE google_event_id IS NULL
                      AND EXISTS (
                        SELECT 1 FROM sessoes s2
                        WHERE (pagamentos.sessao_id = s2.id OR s2.payment_id = pagamentos.id)
                          AND s2.google_event_id IS NOT NULL
                      )
                """)
                result = conn.execute(backfill_query)
                rows_updated = result.rowcount

                # For SQLite, manually filter out collisions by setting back to NULL
                if collision_event_ids:
                    conn.execute(
                        text("""
                        UPDATE pagamentos
                        SET google_event_id = NULL
                        WHERE google_event_id IN :collision_ids
                    """),
                        {"collision_ids": tuple(collision_event_ids)},
                    )

            else:
                logger.warning(
                    "Migration 004 skipped - unsupported database dialect",
                    extra={"context": {"dialect": dialect_name}},
                )
                return

            # Step 3: Log summary to migration_audit
            conn.execute(
                text("""
                INSERT INTO migration_audit (entity_type, entity_id, action, status, details)
                VALUES (:entity_type, NULL, :action, :status, :details)
            """),
                {
                    "entity_type": "pagamento_backfill",
                    "action": "backfill",
                    "status": "success",
                    "details": f'{{"rows_updated": {rows_updated}, "collisions_skipped": {len(collision_event_ids)}}}',
                },
            )

            conn.commit()

            logger.info(
                "Migration 004 applied successfully",
                extra={
                    "context": {
                        "dialect": dialect_name,
                        "rows_updated": rows_updated,
                        "collisions_skipped": len(collision_event_ids),
                    }
                },
            )

    except Exception as e:
        logger.error(
            "Failed to apply Migration 004",
            extra={"context": {"error": str(e)}},
            exc_info=True,
        )
        # Don't raise - app should still start


def ensure_migration_005_unified_flow_flag() -> None:
    """
    Migration 005: Add unified_flow_enabled flag to users table (Phase 3).

    This migration adds a boolean column to control per-user feature flag
    for the unified session-payment flow during canary rollout. Defaults
    to False to maintain backward compatibility.

    This function is idempotent - it can be called multiple times safely.
    """
    try:
        engine = get_engine()
        dialect_name = engine.dialect.name

        with engine.connect() as conn:
            # Check if migration is already applied
            inspector = inspect(engine)
            columns = inspector.get_columns("users")

            # Check if unified_flow_enabled column exists
            has_flag = any(col["name"] == "unified_flow_enabled" for col in columns)

            if has_flag:
                logger.debug(
                    "Migration 005 already applied - unified_flow_enabled column exists",
                    extra={
                        "context": {"table": "users", "column": "unified_flow_enabled"}
                    },
                )
                return

            logger.info(
                "Applying Migration 005 - adding unified_flow_enabled to users",
                extra={"context": {"dialect": dialect_name, "table": "users"}},
            )

            if dialect_name == "postgresql":
                # PostgreSQL: Add column with default False
                conn.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN unified_flow_enabled BOOLEAN NOT NULL DEFAULT FALSE;
                """))
                conn.commit()

            elif dialect_name == "sqlite":
                # SQLite: Add column directly (supports adding columns with defaults)
                conn.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN unified_flow_enabled BOOLEAN NOT NULL DEFAULT 0;
                """))
                conn.commit()

            else:
                logger.warning(
                    "Migration 005 skipped - unsupported database dialect",
                    extra={"context": {"dialect": dialect_name}},
                )
                return

            # Log migration completion
            conn.execute(
                text("""
                INSERT INTO migration_audit (entity_type, entity_id, action, status, details)
                VALUES (:entity_type, NULL, :action, :status, :details)
            """),
                {
                    "entity_type": "user",
                    "action": "add_unified_flow_flag",
                    "status": "success",
                    "details": '{"column": "unified_flow_enabled", "default": false}',
                },
            )

            conn.commit()

            logger.info(
                "Migration 005 applied successfully",
                extra={"context": {"dialect": dialect_name}},
            )

    except Exception as e:
        logger.error(
            "Failed to apply Migration 005",
            extra={"context": {"error": str(e)}},
            exc_info=True,
        )
        # Don't raise - app should still start
