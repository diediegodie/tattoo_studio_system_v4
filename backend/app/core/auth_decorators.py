"""
Authentication helpers for this application.

This project standardizes on Flask-Login session-based authentication.
Use the decorator `@login_required` from `flask_login` on routes that require
authentication and `current_user` to access the logged-in user.

Notes:
- JWT-based decorators were removed to avoid mixed auth models. If an API
  token-based flow is needed in the future, add a dedicated adapter that
  converts token auth into a Flask-Login user before request handling.
"""

from typing import Any, Optional
from flask import g, request, jsonify
from flask_login import current_user
from functools import wraps
from app.core.security import decode_access_token, get_user_from_token


def get_current_user() -> Any:
    """Return current authenticated user, preferring Flask `g.current_user` if set.

    Controllers should prefer `from flask_login import current_user` but this
    helper remains for compatibility with a small number of call sites.
    """
    # Prefer user stored in request-local g (if some adapter set it)
    if hasattr(g, "current_user") and g.current_user:
        return g.current_user

    if current_user and getattr(current_user, "is_authenticated", False):
        return current_user

    return None


def jwt_required(f):
    """Decorator to require JWT authentication for API endpoints.

    Extracts JWT from Authorization header and sets current user.
    If no valid JWT, returns 401.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        token = auth_header.split(" ")[1]
        payload = decode_access_token(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401

        user_data = get_user_from_token(token)
        if not user_data:
            return jsonify({"error": "Invalid token payload"}), 401

        # For testing purposes, create a mock user object
        # In production, this would fetch from database
        from types import SimpleNamespace

        mock_user = SimpleNamespace()
        mock_user.id = user_data["user_id"]
        mock_user.email = user_data["email"]
        mock_user.name = user_data.get("name", "Test User")
        mock_user.avatar_url = None
        mock_user.google_id = None
        mock_user.is_active = True
        mock_user.created_at = None

        g.current_user = mock_user
        return f(*args, **kwargs)

    return decorated_function
