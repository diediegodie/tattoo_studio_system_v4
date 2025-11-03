"""
Common API utilities for consistent response formatting across all controllers.
"""

from typing import Any, Optional

from flask import jsonify, request, current_app, abort


def api_response(
    success: bool, message: str, data: Optional[Any] = None, status_code: int = 200
) -> tuple:
    """
    Standardized API response format for all endpoints.

    Args:
        success: Whether the operation was successful
        message: Human-readable message about the operation
        data: Optional data payload
        status_code: HTTP status code

    Returns:
        Tuple of (json_response, status_code)
    """
    response = {"success": success, "message": message}

    if data is not None:
        response["data"] = data

    return jsonify(response), status_code


def verify_health_token() -> bool:
    """
    Verify the health check token from request headers.

    Returns:
        bool: True if token is valid, False otherwise
    """
    token = request.headers.get("X-Health-Token")
    expected = current_app.config.get("HEALTH_CHECK_TOKEN")
    # If no token expected, deny access (more secure)
    if not expected:
        return False
    return bool(token and token == expected)


def health_endpoint_decorator(f):
    """
    Decorator for health endpoints that verifies token and exempts from rate limiting if valid.
    """
    from functools import wraps

    @wraps(f)
    def wrapper(*args, **kwargs):
        if verify_health_token():
            return f(*args, **kwargs)
        abort(401)

    return wrapper
