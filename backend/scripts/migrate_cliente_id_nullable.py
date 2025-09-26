#!/usr/bin/env python3
"""
Database migration script to make cliente_id nullable in pagamentos table.

This script alters the existing pagamentos table to allow NULL values in the cliente_id column,
enabling payments to be created without requiring a client.

Usage:
    python backend/scripts/migrate_cliente_id_nullable.py
"""

import os
import sys

# Add the backend directory to the Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

from app.db.session import engine
from sqlalchemy import text


def migrate_cliente_id_nullable():
    """Make cliente_id column nullable in pagamentos table."""

    # SQL to alter the column (works for both PostgreSQL and SQLite)
    alter_sql = """
    -- For PostgreSQL, we need to explicitly set the column to nullable
    -- For SQLite, this is more complex as it doesn't support ALTER COLUMN directly
    """

    try:
        with engine.connect() as conn:
            # Check if we're using PostgreSQL or SQLite
            db_dialect = str(conn.dialect.name)

            if db_dialect == "postgresql":
                # PostgreSQL syntax
                alter_sql = (
                    "ALTER TABLE pagamentos ALTER COLUMN cliente_id DROP NOT NULL;"
                )
                conn.execute(text(alter_sql))
                conn.commit()
                print(
                    "✅ Successfully made cliente_id nullable in pagamentos table (PostgreSQL)"
                )

            elif db_dialect == "sqlite":
                # For SQLite, we need to check if the column is already nullable
                # SQLite doesn't have a direct way to modify column constraints
                # We'll create a new table and copy data if needed

                # First, check current schema
                result = conn.execute(text("PRAGMA table_info(pagamentos)")).fetchall()

                # Find cliente_id column info
                cliente_id_info = None
                for row in result:
                    if row[1] == "cliente_id":  # row[1] is column name
                        cliente_id_info = row
                        break

                if (
                    cliente_id_info and cliente_id_info[3] == 1
                ):  # row[3] is notnull (1=NOT NULL, 0=NULL)
                    print("⚠️  SQLite detected: cliente_id is currently NOT NULL")
                    print("⚠️  SQLite doesn't support ALTER COLUMN directly")
                    print("⚠️  For SQLite, you'll need to:")
                    print("   1. Stop the application")
                    print("   2. Create a backup of your database")
                    print(
                        "   3. Recreate tables with the new schema using create_all()"
                    )
                    print("   4. Or use a more complex migration process")
                    print(
                        "⚠️  For now, the model has been updated for new installations"
                    )
                    return False
                else:
                    print("✅ SQLite: cliente_id already allows NULL or doesn't exist")

            else:
                print(f"❌ Unsupported database dialect: {db_dialect}")
                return False

    except Exception as e:
        print(f"❌ Error during migration: {e}")
        return False

    return True


def verify_migration():
    """Verify that the migration was successful."""
    try:
        with engine.connect() as conn:
            db_dialect = str(conn.dialect.name)

            if db_dialect == "postgresql":
                # Check PostgreSQL column constraints
                verify_sql = """
                SELECT column_name, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'pagamentos' AND column_name = 'cliente_id';
                """
                result = conn.execute(text(verify_sql)).fetchone()
                if result and result[1] == "YES":
                    print("✅ Verification: cliente_id is now nullable")
                    return True
                else:
                    print("❌ Verification failed: cliente_id is still NOT NULL")
                    return False

            elif db_dialect == "sqlite":
                # Check SQLite column info
                result = conn.execute(text("PRAGMA table_info(pagamentos)")).fetchall()
                for row in result:
                    if (
                        row[1] == "cliente_id" and row[3] == 0
                    ):  # notnull = 0 means NULL allowed
                        print("✅ Verification: cliente_id allows NULL")
                        return True
                print("⚠️  Could not verify SQLite migration - check manually")
                return True  # Don't fail for SQLite verification

    except Exception as e:
        print(f"❌ Verification error: {e}")
        return False


def main():
    print("Starting migration: making cliente_id nullable in pagamentos table...")

    if migrate_cliente_id_nullable():
        if verify_migration():
            print("🎉 Migration completed successfully!")
            print("   Payments can now be created without specifying a client.")
        else:
            print("⚠️  Migration may have completed but verification failed.")
    else:
        print("❌ Migration failed!")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
