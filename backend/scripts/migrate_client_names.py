#!/usr/bin/env python3
"""
One-time migration script to normalize existing client names in the database.

This script:
1. Connects to the database
2. Retrieves all existing client records
3. Applies normalize_display_name() to each client's name
4. Updates the records with normalized names
5. Commits the changes

Run this script once after deploying the client repository refactor.
"""

import sys
import os
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.session import SessionLocal
from app.db.base import Client as DbClient
from app.utils.client_utils import normalize_display_name


def migrate_client_names():
    """Migrate existing client names to normalized format."""
    print("Starting client name normalization migration...")

    session = SessionLocal()

    try:
        # Get all clients
        clients = session.query(DbClient).all()
        print(f"Found {len(clients)} client records to process.")

        updated_count = 0

        for client in clients:
            original_name = client.name or ""
            normalized_name = normalize_display_name(original_name)

            # Always update to ensure consistent normalization
            if original_name != normalized_name or True:  # Force update all records
                print(
                    f"Updating client {client.id}: '{original_name}' -> '{normalized_name}'"
                )
                client.name = normalized_name
                updated_count += 1
            else:
                print(f"Client {client.id} already normalized: '{original_name}'")

        # Commit all changes
        session.commit()
        print(
            f"Migration complete! Updated {updated_count} out of {len(clients)} client records."
        )

    except Exception as e:
        session.rollback()
        print(f"Error during migration: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    migrate_client_names()
