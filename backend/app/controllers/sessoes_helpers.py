"""
Helper functions for sessoes module.
Contains utility functions and dependency injection factories.
"""

import logging
from typing import Optional

from app.repositories.user_repo import UserRepository
from app.services.user_service import UserService
from app.db.base import Client
from flask import jsonify

logger = logging.getLogger(__name__)


def api_response(
    success: bool, message: str, data: dict | list | None = None, status_code: int = 200
):
    """Consistent JSON API response used across controllers."""
    return jsonify({"success": success, "message": message, "data": data}), status_code


def _get_user_service() -> UserService:
    """Dependency injection factory for UserService."""
    # Import SessionLocal lazily so tests can set DATABASE_URL before session factory
    from app.db.session import SessionLocal

    db_session = SessionLocal()
    user_repo = UserRepository(db_session)
    return UserService(user_repo)


def find_or_create_client(db_session, cliente_nome: str) -> Optional[int]:
    """
    Find an existing client by name or create a new one.

    Args:
        db_session: SQLAlchemy database session
        cliente_nome: Name of the client to find or create

    Returns:
        Client ID if successful, None otherwise
    """
    if not cliente_nome or not cliente_nome.strip():
        return None

    cliente_nome = cliente_nome.strip()

    # Search for existing client with exact name match (case-insensitive)
    existing_client = (
        db_session.query(Client).filter(Client.name.ilike(cliente_nome)).first()
    )

    if existing_client:
        logger.info(
            f"Found existing client: {existing_client.name} (ID: {existing_client.id})"
        )
        return existing_client.id

    # Create new client if not found
    try:
        new_client = Client(
            name=cliente_nome,
            jotform_submission_id=None,  # Manual clients have no Jotform ID
        )
        db_session.add(new_client)
        db_session.flush()  # Get the ID without committing the transaction
        logger.info(f"Created new client: {new_client.name} (ID: {new_client.id})")
        return new_client.id
    except Exception as e:
        logger.error(f"Error creating client: {e}")
        return None
