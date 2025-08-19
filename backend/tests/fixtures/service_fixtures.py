"""
Service test fixtures following SOLID principles.

This module provides fixtures for testing services with proper dependency injection
and mocking of repository dependencies.
"""

import pytest
from unittest.mock import Mock

# Import after ensuring paths are set up
from tests.config import setup_test_imports

setup_test_imports()

try:
    from services.user_service import UserService
    from tests.factories.repository_factories import UserRepositoryFactory

    SERVICE_IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import service modules: {e}")
    SERVICE_IMPORTS_AVAILABLE = False


@pytest.fixture
def user_service_with_empty_repo():
    """Create UserService with empty repository mock."""
    if not SERVICE_IMPORTS_AVAILABLE:
        return Mock()

    mock_repo = UserRepositoryFactory.create_mock_full()
    return UserService(user_repository=mock_repo)


@pytest.fixture
def user_service_with_existing_user():
    """Create UserService with repository containing one test user."""
    if not SERVICE_IMPORTS_AVAILABLE:
        return Mock()

    user_data = {
        "email": "test@example.com",
        "password_hash": "hashed_password",
        "name": "Test User",
        "phone": "1234567890",
        "is_verified": True,
    }

    mock_repo = UserRepositoryFactory.create_populated_mock(user_data)
    return UserService(user_repository=mock_repo)


@pytest.fixture
def user_service_with_failing_repo():
    """Create UserService with repository that raises exceptions."""
    if not SERVICE_IMPORTS_AVAILABLE:
        return Mock()

    mock_repo = UserRepositoryFactory.create_mock_full()
    # Configure to raise exceptions for testing error handling
    mock_repo.create.side_effect = Exception("Database error")
    mock_repo.get_by_email.side_effect = Exception("Database error")

    return UserService(user_repository=mock_repo)


@pytest.fixture
def isolated_user_service():
    """Create UserService with completely isolated dependencies for unit testing."""
    if not SERVICE_IMPORTS_AVAILABLE:
        return Mock()

    # Create a fresh mock repository for each test
    mock_repo = UserRepositoryFactory.create_mock_full()
    service = UserService(user_repository=mock_repo)

    # Provide access to the mock for test assertions
    service._test_repo_mock = mock_repo

    return service


# Service factory functions for more complex test scenarios
class ServiceTestFactory:
    """Factory for creating service instances with different configurations."""

    @staticmethod
    def create_user_service_with_mock_behavior(repo_behavior: dict):
        """
        Create UserService with custom repository behavior.

        Args:
            repo_behavior: Dict defining what each repository method should return
                          e.g., {'get_by_email': mock_user, 'create': None}
        """
        if not SERVICE_IMPORTS_AVAILABLE:
            return Mock()

        mock_repo = UserRepositoryFactory.create_mock_full()

        for method_name, return_value in repo_behavior.items():
            if hasattr(mock_repo, method_name):
                getattr(mock_repo, method_name).return_value = return_value

        return UserService(user_repository=mock_repo)

    @staticmethod
    def create_user_service_with_side_effects(side_effects: dict):
        """
        Create UserService with repository methods that have side effects.

        Args:
            side_effects: Dict defining side effects for repository methods
                         e.g., {'create': Exception("Error"), 'get_by_id': [user1, user2]}
        """
        if not SERVICE_IMPORTS_AVAILABLE:
            return Mock()

        mock_repo = UserRepositoryFactory.create_mock_full()

        for method_name, side_effect in side_effects.items():
            if hasattr(mock_repo, method_name):
                getattr(mock_repo, method_name).side_effect = side_effect

        return UserService(user_repository=mock_repo)


# Verification helpers for service testing
class ServiceTestVerifiers:
    """Helper functions for verifying service behavior in tests."""

    @staticmethod
    def verify_repository_method_called(
        service, method_name: str, expected_call_count: int = 1
    ):
        """Verify that a repository method was called the expected number of times."""
        if hasattr(service, "_test_repo_mock"):
            mock_repo = service._test_repo_mock
            method = getattr(mock_repo, method_name)
            assert (
                method.call_count == expected_call_count
            ), f"Expected {method_name} to be called {expected_call_count} times, but was called {method.call_count} times"

    @staticmethod
    def verify_repository_method_called_with(
        service, method_name: str, *expected_args, **expected_kwargs
    ):
        """Verify that a repository method was called with specific arguments."""
        if hasattr(service, "_test_repo_mock"):
            mock_repo = service._test_repo_mock
            method = getattr(mock_repo, method_name)
            method.assert_called_with(*expected_args, **expected_kwargs)

    @staticmethod
    def verify_no_repository_calls(service, method_name: str):
        """Verify that a repository method was never called."""
        if hasattr(service, "_test_repo_mock"):
            mock_repo = service._test_repo_mock
            method = getattr(mock_repo, method_name)
            assert (
                not method.called
            ), f"Expected {method_name} to not be called, but it was called {method.call_count} times"

    @staticmethod
    def get_repository_call_args(service, method_name: str, call_index: int = 0):
        """Get the arguments used in a specific call to a repository method."""
        if hasattr(service, "_test_repo_mock"):
            mock_repo = service._test_repo_mock
            method = getattr(mock_repo, method_name)
            if method.call_args_list and len(method.call_args_list) > call_index:
                return method.call_args_list[call_index]
        return None


# Parametrized test data for common service test scenarios
SERVICE_TEST_SCENARIOS = {
    "user_creation_success": {
        "repo_behavior": {
            "get_by_email": None,  # User doesn't exist
            "create": {"id": 1, "email": "test@example.com"},  # Creation succeeds
        },
        "expected_outcome": "success",
    },
    "user_creation_duplicate_email": {
        "repo_behavior": {
            "get_by_email": {"id": 1, "email": "test@example.com"},  # User exists
            "create": None,
        },
        "expected_outcome": "duplicate_error",
    },
    "user_creation_database_error": {
        "side_effects": {
            "get_by_email": None,
            "create": Exception("Database connection failed"),
        },
        "expected_outcome": "database_error",
    },
}


@pytest.fixture(params=SERVICE_TEST_SCENARIOS.keys())
def user_service_test_scenario(request):
    """Parametrized fixture for testing different user service scenarios."""
    scenario_name = request.param
    scenario_config = SERVICE_TEST_SCENARIOS[scenario_name]

    if not SERVICE_IMPORTS_AVAILABLE:
        return {
            "service": Mock(),
            "scenario": scenario_name,
            "expected": scenario_config["expected_outcome"],
        }

    if "repo_behavior" in scenario_config:
        service = ServiceTestFactory.create_user_service_with_mock_behavior(
            scenario_config["repo_behavior"]
        )
    elif "side_effects" in scenario_config:
        service = ServiceTestFactory.create_user_service_with_side_effects(
            scenario_config["side_effects"]
        )
    else:
        service = UserService(user_repository=UserRepositoryFactory.create_mock_full())

    return {
        "service": service,
        "scenario": scenario_name,
        "expected": scenario_config["expected_outcome"],
    }
