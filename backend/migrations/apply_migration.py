#!/usr/bin/env python3
"""
Migration script to make jotform_submission_id nullable in clients table.
This script works with both SQLite and PostgreSQL.

⚠️ NOTE: This is a standalone migration script for manual use.
The app now applies this migration automatically on startup via
app/db/migrations.py - you don't need to run this manually unless
troubleshooting.

Usage:
    python apply_migration.py [database_url]

If database_url is not provided, tries DATABASE_URL env var, then falls back to SQLite.
"""

import os
import sys
from pathlib import Path
import sqlite3
from typing import Optional


def apply_migration():
    """Apply the migration to make jotform_submission_id nullable."""

    # Get database URL from command line, env, or fallback to SQLite
    if len(sys.argv) > 1:
        database_url = sys.argv[1]
    else:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            # Fallback to local SQLite
            project_root = Path(__file__).parent.parent.parent
            sqlite_path = project_root / "tattoo_studio_dev.db"
            database_url = f"sqlite:///{sqlite_path}"

    # Extract path for SQLite
    if database_url.startswith("sqlite:///"):
        db_path = database_url.replace("sqlite:///", "")
    else:
        print(f"Error: This migration script only supports SQLite databases")
        print(f"Current DATABASE_URL: {database_url}")
        return False

    print(f"Applying migration to database: {db_path}")

    # Check if database exists
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return False

    # Read migration SQL
    migration_file = Path(__file__).parent / "001_make_jotform_nullable.sql"
    with open(migration_file, "r") as f:
        migration_sql = f.read()

    conn = None
    try:
        # Connect and apply migration
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check if migration is needed
        cursor.execute("PRAGMA table_info(clients)")
        columns = cursor.fetchall()

        jotform_col = None
        for col in columns:
            if col[1] == "jotform_submission_id":
                jotform_col = col
                break

        if jotform_col is None:
            print("Error: clients table does not have jotform_submission_id column")
            return False

        # Check if column is already nullable (notnull=0 means nullable)
        is_nullable = jotform_col[3] == 0

        if is_nullable:
            print(
                "✓ Migration already applied: jotform_submission_id is already nullable"
            )
            return True

        print("Applying migration...")
        cursor.executescript(migration_sql)
        conn.commit()

        # Verify migration
        cursor.execute("PRAGMA table_info(clients)")
        columns_after = cursor.fetchall()

        for col in columns_after:
            if col[1] == "jotform_submission_id":
                if col[3] == 0:  # notnull=0 means nullable
                    print("✓ Migration applied successfully!")
                    print("  jotform_submission_id is now nullable")
                    return True
                else:
                    print("✗ Migration failed: column is still NOT NULL")
                    return False

        print("✗ Migration failed: column not found after migration")
        return False

    except Exception as e:
        print(f"✗ Error applying migration: {e}")
        return False
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    success = apply_migration()
    sys.exit(0 if success else 1)
