"""
Sample data fixtures for integration testing.

This module provides sample data fixtures for testing various components
of the tattoo studio system.
"""

from datetime import datetime, timezone

import pytest
# Set up test environment paths
from tests.config.test_paths import setup_test_environment

setup_test_environment()

try:
    # Quick availability check for Flask and SQLAlchemy. Do NOT import
    # application modules that may create engines at module import time.
    from datetime import datetime, timedelta, timezone

    import flask  # type: ignore
    import jwt
    from sqlalchemy import text  # type: ignore

    FLASK_IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Flask integration dependencies not available: {e}")
    FLASK_IMPORTS_AVAILABLE = False


@pytest.fixture
def sample_client_data():
    """Create sample client data for testing."""
    return {
        "name": "John Doe",
        "email": "john.doe@example.com",
        "phone": "+1234567890",
        "submission_id": "jotform_123456",
        "birth_date": "1990-01-15",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


@pytest.fixture
def sample_appointment_data():
    """Create sample appointment data for testing."""
    return {
        "client_id": 1,
        "date": "2024-12-25",
        "time": "14:00",
        "service": "Tatuagem Pequena",
        "status": "agendado",
        "notes": "First tattoo session",
    }


@pytest.fixture
def mock_jotform_response():
    """Create mock JotForm API response data."""
    return {
        "responseCode": 200,
        "message": "success",
        "content": [
            {
                "id": "123456",
                "form_id": "242871033645151",
                "ip": "192.168.1.1",
                "created_at": "2024-01-15 10:30:00",
                "status": "ACTIVE",
                "answers": {
                    "3": {"answer": "John Doe"},
                    "4": {"answer": "john.doe@example.com"},
                    "5": {"answer": "+1234567890"},
                    "6": {"answer": "1990-01-15"},
                },
            }
        ],
    }
