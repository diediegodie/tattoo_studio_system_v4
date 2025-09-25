"""
Common API utilities for consistent response formatting across all controllers.
"""

from typing import Any, Optional

from flask import jsonify


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
