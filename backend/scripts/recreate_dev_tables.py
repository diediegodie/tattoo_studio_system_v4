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


def recreate_tables_with_nullable_cliente_id():
    """Recreate all tables with current schema (nullable cliente_id)."""

    # Create backup of current database
    db_path = "tattoo_studio_dev.db"
    if os.path.exists(db_path):
        backup_path = (
            f"tattoo_studio_dev_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        )
        shutil.copy2(db_path, backup_path)
        print(f"✅ Created backup: {backup_path}")

    try:
        # Drop all existing tables
        Base.metadata.drop_all(engine)
        print("🗑️  Dropped all existing tables")

        # Create all tables with new schema
        Base.metadata.create_all(engine)
        print("✅ Created all tables with new schema (nullable cliente_id)")

        print("🎉 Migration completed successfully!")
        print("   WARNING: All data has been lost. This is only for development.")

        return True

    except Exception as e:
        print(f"❌ Error during migration: {e}")
        if os.path.exists(backup_path):
            print(f"🔄 Backup available at: {backup_path}")
        return False


if __name__ == "__main__":
    print("🚨 WARNING: This will DELETE ALL DATA in the database!")
    print("Only use this for development environments.")

    response = input("Continue? (yes/no): ").lower().strip()
    if response == "yes":
        recreate_tables_with_nullable_cliente_id()
    else:
        print("Migration cancelled.")
