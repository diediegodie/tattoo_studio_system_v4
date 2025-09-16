"""
Pytest markers and configuration for the tattoo studio system tests.

This module contains pytest marker definitions and collection modification
functions that were moved from conftest.py to maintain file size limits
and improve organization. These configurations ensure consistent test
categorization and discovery across the test suite.
"""

import pytest


def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "auth: mark test as authentication-related")
    config.addinivalue_line("markers", "security: mark test as security-related")
    config.addinivalue_line("markers", "api: mark test as API endpoint test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "postgres: mark test as requiring PostgreSQL")
    config.addinivalue_line("markers", "google: mark test as requiring Google API")
    config.addinivalue_line("markers", "controllers: mark test as controller-related")
    config.addinivalue_line("markers", "sessions: mark test as session-related")
    config.addinivalue_line("markers", "clients: mark test as client-related")
    config.addinivalue_line("markers", "database: mark test as database-related")
    config.addinivalue_line("markers", "performance: mark test as performance-related")
    config.addinivalue_line("markers", "services: mark test as service layer test")
    config.addinivalue_line("markers", "appointment: mark test as appointment-related")
    config.addinivalue_line("markers", "artist: mark test as artist-related")
    config.addinivalue_line("markers", "repositories: mark test as repository test")
    config.addinivalue_line("markers", "user: mark test as user-related")
    config.addinivalue_line("markers", "service_layer: mark test as service layer test")
    config.addinivalue_line("markers", "docker: mark test as requiring Docker")
    config.addinivalue_line(
        "markers", "client: mark test as related to client operations"
    )
    config.addinivalue_line(
        "markers", "search: mark test as related to search functionality"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test items during collection."""
    for item in items:
        # Add markers based on test file location
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        if "auth" in str(item.fspath) or "auth" in item.name:
            item.add_marker(pytest.mark.auth)

        if "security" in str(item.fspath) or "security" in item.name:
            item.add_marker(pytest.mark.security)

        if "postgres" in str(item.fspath) or "postgres" in item.name:
            item.add_marker(pytest.mark.postgres)

        if "calendar" in str(item.fspath) or "google" in str(item.fspath):
            item.add_marker(pytest.mark.google)

        # Add sessoes-specific markers
        if "sessoes" in str(item.fspath) or "sessoes" in item.name:
            item.add_marker(pytest.mark.controllers)
            item.add_marker(pytest.mark.sessions)

        # Add general controller markers
        if "controller" in str(item.fspath):
            item.add_marker(pytest.mark.controllers)

        # Add service layer markers
        if "service" in str(item.fspath) or "service" in item.name:
            item.add_marker(pytest.mark.services)
            item.add_marker(pytest.mark.service_layer)

        # Add repository markers
        if "repo" in str(item.fspath) or "repository" in str(item.fspath):
            item.add_marker(pytest.mark.repositories)


@pytest.fixture
def response_helper():
    """Simple response helper for integration tests."""

    class ResponseHelper:
        @staticmethod
        def assert_html_response(response, expected_status=200):
            assert response.status_code == expected_status
            return response.get_data(as_text=True)

        @staticmethod
        def assert_json_response(response, expected_status=200):
            assert response.status_code == expected_status
            return response.get_json()

        @staticmethod
        def assert_redirect_response(response):
            assert response.status_code in (301, 302, 303, 307, 308)
            return response.headers.get("Location")

    return ResponseHelper()
