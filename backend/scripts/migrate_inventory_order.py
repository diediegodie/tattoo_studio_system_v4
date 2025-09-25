"""
Migration script to make the 'order' column nullable in the inventory table.

This script modifies the SQLite database schema to allow NULL values in the 'order' column.
"""

import os
import sqlite3
import sys
from pathlib import Path


def migrate_inventory_order(database_url=None):
    """Migrate the inventory table to make 'order' column nullable."""

    # Extract database path from DATABASE_URL
    if database_url:
        if database_url.startswith("sqlite:///"):
            db_path = database_url[10:]  # Remove 'sqlite:///'
        else:
            raise ValueError(f"Unsupported database URL: {database_url}")
    else:
        # Default to environment variable
        database_url = os.getenv("DATABASE_URL")
        if database_url and database_url.startswith("sqlite:///"):
            db_path = database_url[10:]
        else:
            raise ValueError("DATABASE_URL not set or not SQLite")

    print(f"Migrating database at: {db_path}")

    # Connect to database
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    try:
        # Check current schema
        cur.execute("PRAGMA table_info('inventory');")
        columns = cur.fetchall()
        order_col = next((col for col in columns if col[1] == "order"), None)

        if not order_col:
            raise ValueError("Column 'order' not found in inventory table")

        print(f"Current 'order' column: {order_col}")

        # SQLite doesn't support ALTER COLUMN to change NULL constraints directly
        # We need to recreate the table with the new schema
        if order_col[3] == 1:  # notnull == 1 means NOT NULL
            print("Making 'order' column nullable...")

            # Get all data
            cur.execute('SELECT id, nome, quantidade, "order" FROM inventory')
            data = cur.fetchall()

            # Drop existing table
            cur.execute("DROP TABLE inventory")

            # Recreate table with nullable 'order' column
            cur.execute(
                """
                CREATE TABLE inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT,
                    quantidade INTEGER,
                    "order" INTEGER NULL DEFAULT 0
                );
            """
            )

            # Insert data back
            cur.executemany(
                'INSERT INTO inventory (id, nome, quantidade, "order") VALUES (?, ?, ?, ?)',
                data,
            )

            conn.commit()
            print("Migration completed successfully")
        else:
            print("'order' column is already nullable")

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_inventory_order()
