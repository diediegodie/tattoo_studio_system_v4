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

import os
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.logging_config import get_logger
from app.db.base import Client as DbClient
from app.db.session import SessionLocal
from app.utils.client_utils import normalize_display_name

logger = get_logger(__name__)


def migrate_client_names():
    """Migrate existing client names to normalized format."""
    logger.info(
        "Starting client name normalization migration",
        extra={"context": {"action": "migrate_client_names"}},
    )

    session = SessionLocal()

    try:
        # Get all clients
        clients = session.query(DbClient).all()
        logger.info(
            "Client records to process",
            extra={"context": {"count": len(clients)}},
        )

        updated_count = 0

        for client in clients:
            original_name = client.name or ""
            normalized_name = normalize_display_name(original_name)

            # Always update to ensure consistent normalization
            if original_name != normalized_name or True:  # Force update all records
                logger.info(
                    "Updating client name",
                    extra={
                        "context": {
                            "client_id": client.id,
                            "original": original_name,
                            "normalized": normalized_name,
                        }
                    },
                )
                client.name = normalized_name
                updated_count += 1
            else:
                logger.info(
                    "Client already normalized",
                    extra={"context": {"client_id": client.id, "name": original_name}},
                )

        # Commit all changes
        session.commit()
        logger.info(
            "Migration complete",
            extra={"context": {"updated": updated_count, "total": len(clients)}},
        )

    except Exception as e:
        session.rollback()
        logger.error(
            "Error during migration",
            extra={"context": {"error": str(e)}},
            exc_info=True,
        )
        raise
    finally:
        session.close()


if __name__ == "__main__":
    migrate_client_names()
