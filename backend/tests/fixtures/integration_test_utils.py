"""
Testing utilities for integration testing.

This module provides helper classes and utilities for testing Flask responses
and other testing infrastructure.
"""

import pytest
from datetime import datetime, timezone

# Set up test environment paths
from tests.config.test_paths import setup_test_environment

setup_test_environment()

try:
    # Quick availability check for Flask and SQLAlchemy. Do NOT import
    # application modules that may create engines at module import time.
    import flask  # type: ignore
    from sqlalchemy import text  # type: ignore
    import jwt
    from datetime import datetime, timedelta, timezone

    FLASK_IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Flask integration dependencies not available: {e}")
    FLASK_IMPORTS_AVAILABLE = False


class FlaskTestResponse:
    """Helper class for testing Flask responses."""

    @staticmethod
    def assert_json_response(response, expected_status=200):
        """Assert that response is JSON with expected status."""
        assert response.status_code == expected_status
        assert response.content_type == "application/json"
        return response.get_json()

    @staticmethod
    def assert_html_response(response, expected_status=200):
        """Assert that response is HTML with expected status."""
        assert response.status_code == expected_status
        assert "text/html" in response.content_type
        return response.get_data(as_text=True)

    @staticmethod
    def assert_redirect_response(response, expected_location=None):
        """Assert that response is a redirect."""
        assert response.status_code in [301, 302, 303, 307, 308]
        if expected_location:
            assert expected_location in response.location
        return response.location
