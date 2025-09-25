"""
Helper functions for sessoes module.
Contains utility functions and dependency injection factories.
"""

import logging
from typing import Union

from app.repositories.user_repo import UserRepository
from app.services.user_service import UserService
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
