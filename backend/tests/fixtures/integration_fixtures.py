"""
Integration test fixtures and utilities - Main module importing from split files.

This module serves as the main entry point for integration test fixtures.
All fixtures have been split into separate modules for better maintainability:

- integration_database_fixtures.py: Database setup and session fixtures
- integration_app_fixtures.py: Flask app, client, and runner fixtures
- integration_auth_fixtures.py: Authentication-related fixtures
- integration_data_fixtures.py: Sample data fixtures
- integration_test_utils.py: Testing utilities and helper classes

This file imports all fixtures to maintain backward compatibility.
"""

from .integration_app_fixtures import app, client, runner
from .integration_auth_fixtures import (
    auth_headers,
    authenticated_client,
    mock_authenticated_user,
)
from .integration_data_fixtures import (
    mock_jotform_response,
    sample_appointment_data,
    sample_client_data,
)

# Import all fixtures from split modules
from .integration_database_fixtures import (
    database_transaction_isolator,
    db_session,
    test_database,
)
from .integration_test_utils import FlaskTestResponse, response_helper

# Re-export all fixtures and utilities for pytest discovery
__all__ = [
    "test_database",
    "app",
    "client",
    "runner",
    "db_session",
    "auth_headers",
    "mock_authenticated_user",
    "authenticated_client",
    "sample_client_data",
    "sample_appointment_data",
    "mock_jotform_response",
    "database_transaction_isolator",
    "FlaskTestResponse",
    "response_helper",
]
