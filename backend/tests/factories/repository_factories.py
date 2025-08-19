"""
Repository test factories following Interface Segregation Principle.

This module provides mock factories for repository interfaces, ensuring
tests only depend on the specific interfaces they need.
"""

from unittest.mock import Mock, MagicMock
from typing import Optional, List

# Import after ensuring paths are set up
from tests.config import setup_test_imports

setup_test_imports()

try:
    from domain.interfaces import (
        IUserReader,
        IUserWriter,
        IUserRepository,
        IAppointmentReader,
        IAppointmentWriter,
        IAppointmentRepository,
        IInventoryReader,
        IInventoryWriter,
        IInventoryRepository,
    )
    from domain.entities import User, Appointment, InventoryItem

    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import domain modules: {e}")
    IMPORTS_AVAILABLE = False


class UserRepositoryFactory:
    """Factory for creating User repository mocks following Interface Segregation."""

    @staticmethod
    def create_mock_reader() -> Mock:
        """Create mock that only implements IUserReader operations."""
        if not IMPORTS_AVAILABLE:
            return Mock()

        mock_reader = Mock(spec=IUserReader)

        # Set up default return values
        mock_reader.get_by_id.return_value = None
        mock_reader.get_by_email.return_value = None
        mock_reader.get_by_google_id.return_value = None

        return mock_reader

    @staticmethod
    def create_mock_writer() -> Mock:
        """Create mock that only implements IUserWriter operations."""
        if not IMPORTS_AVAILABLE:
            return Mock()

        mock_writer = Mock(spec=IUserWriter)

        # Set up default return values
        mock_writer.create.return_value = None
        mock_writer.update.return_value = None
        mock_writer.delete.return_value = False

        return mock_writer

    @staticmethod
    def create_mock_full() -> Mock:
        """Create full repository mock implementing IUserRepository."""
        if not IMPORTS_AVAILABLE:
            return Mock()

        mock_repo = Mock(spec=IUserRepository)

        # Set up default return values for read operations
        mock_repo.get_by_id.return_value = None
        mock_repo.get_by_email.return_value = None
        mock_repo.get_by_google_id.return_value = None

        # Set up default return values for write operations
        mock_repo.create.return_value = None
        mock_repo.update.return_value = None
        mock_repo.delete.return_value = False

        return mock_repo

    @staticmethod
    def create_populated_mock(user_data: dict = None) -> Mock:
        """Create mock repository with pre-populated data."""
        if not IMPORTS_AVAILABLE:
            return Mock()

        mock_repo = UserRepositoryFactory.create_mock_full()

        if user_data:
            mock_user = User(**user_data) if IMPORTS_AVAILABLE else Mock()
            mock_repo.get_by_id.return_value = mock_user
            mock_repo.get_by_email.return_value = mock_user
            mock_repo.get_by_google_id.return_value = mock_user
            mock_repo.create.return_value = mock_user
            mock_repo.update.return_value = mock_user
            mock_repo.delete.return_value = True

        return mock_repo


class AppointmentRepositoryFactory:
    """Factory for creating Appointment repository mocks."""

    @staticmethod
    def create_mock_reader() -> Mock:
        """Create mock that only implements IAppointmentReader operations."""
        if not IMPORTS_AVAILABLE:
            return Mock()

        mock_reader = Mock(spec=IAppointmentReader)

        # Set up default return values
        mock_reader.get_by_id.return_value = None
        mock_reader.get_by_user_id.return_value = []
        mock_reader.get_by_date_range.return_value = []

        return mock_reader

    @staticmethod
    def create_mock_writer() -> Mock:
        """Create mock that only implements IAppointmentWriter operations."""
        if not IMPORTS_AVAILABLE:
            return Mock()

        mock_writer = Mock(spec=IAppointmentWriter)

        # Set up default return values
        mock_writer.create.return_value = None
        mock_writer.update.return_value = None
        mock_writer.cancel.return_value = False

        return mock_writer

    @staticmethod
    def create_mock_full() -> Mock:
        """Create full appointment repository mock."""
        if not IMPORTS_AVAILABLE:
            return Mock()

        mock_repo = Mock(spec=IAppointmentRepository)

        # Set up default return values for read operations
        mock_repo.get_by_id.return_value = None
        mock_repo.get_by_user_id.return_value = []
        mock_repo.get_by_date_range.return_value = []

        # Set up default return values for write operations
        mock_repo.create.return_value = None
        mock_repo.update.return_value = None
        mock_repo.cancel.return_value = False

        return mock_repo

    @staticmethod
    def create_populated_mock(appointment_data: dict = None) -> Mock:
        """Create mock repository with pre-populated appointment data."""
        if not IMPORTS_AVAILABLE:
            return Mock()

        mock_repo = AppointmentRepositoryFactory.create_mock_full()

        if appointment_data:
            mock_appointment = (
                Appointment(**appointment_data) if IMPORTS_AVAILABLE else Mock()
            )
            mock_repo.get_by_id.return_value = mock_appointment
            mock_repo.get_by_user_id.return_value = [mock_appointment]
            mock_repo.get_by_date_range.return_value = [mock_appointment]
            mock_repo.create.return_value = mock_appointment
            mock_repo.update.return_value = mock_appointment
            mock_repo.cancel.return_value = True

        return mock_repo


class InventoryRepositoryFactory:
    """Factory for creating Inventory repository mocks."""

    @staticmethod
    def create_mock_reader() -> Mock:
        """Create mock that only implements IInventoryReader operations."""
        if not IMPORTS_AVAILABLE:
            return Mock()

        mock_reader = Mock(spec=IInventoryReader)

        # Set up default return values
        mock_reader.get_by_id.return_value = None
        mock_reader.get_all.return_value = []
        mock_reader.get_low_stock_items.return_value = []
        mock_reader.search_by_name.return_value = []

        return mock_reader

    @staticmethod
    def create_mock_writer() -> Mock:
        """Create mock that only implements IInventoryWriter operations."""
        if not IMPORTS_AVAILABLE:
            return Mock()

        mock_writer = Mock(spec=IInventoryWriter)

        # Set up default return values
        mock_writer.create.return_value = None
        mock_writer.update.return_value = None
        mock_writer.delete.return_value = False
        mock_writer.update_stock.return_value = False

        return mock_writer

    @staticmethod
    def create_mock_full() -> Mock:
        """Create full inventory repository mock."""
        if not IMPORTS_AVAILABLE:
            return Mock()

        mock_repo = Mock(spec=IInventoryRepository)

        # Set up default return values for read operations
        mock_repo.get_by_id.return_value = None
        mock_repo.get_all.return_value = []
        mock_repo.get_low_stock_items.return_value = []
        mock_repo.search_by_name.return_value = []

        # Set up default return values for write operations
        mock_repo.create.return_value = None
        mock_repo.update.return_value = None
        mock_repo.delete.return_value = False
        mock_repo.update_stock.return_value = False

        return mock_repo

    @staticmethod
    def create_populated_mock(inventory_data: dict = None) -> Mock:
        """Create mock repository with pre-populated inventory data."""
        if not IMPORTS_AVAILABLE:
            return Mock()

        mock_repo = InventoryRepositoryFactory.create_mock_full()

        if inventory_data:
            mock_item = InventoryItem(**inventory_data) if IMPORTS_AVAILABLE else Mock()
            mock_repo.get_by_id.return_value = mock_item
            mock_repo.get_all.return_value = [mock_item]
            mock_repo.search_by_name.return_value = [mock_item]
            mock_repo.create.return_value = mock_item
            mock_repo.update.return_value = mock_item
            mock_repo.delete.return_value = True
            mock_repo.update_stock.return_value = True

        return mock_repo


class RepositoryFactoryUtils:
    """Utility functions for repository factory operations."""

    @staticmethod
    def configure_mock_to_raise_error(
        mock_repo: Mock, method_name: str, error: Exception
    ):
        """Configure a mock repository method to raise a specific error."""
        getattr(mock_repo, method_name).side_effect = error

    @staticmethod
    def configure_mock_to_return_sequence(
        mock_repo: Mock, method_name: str, return_values: list
    ):
        """Configure a mock repository method to return a sequence of values."""
        getattr(mock_repo, method_name).side_effect = return_values

    @staticmethod
    def verify_mock_called_with_domain_entity(
        mock_repo: Mock, method_name: str, entity_type: type
    ):
        """Verify that a mock repository method was called with a domain entity of the correct type."""
        method = getattr(mock_repo, method_name)
        assert method.called, f"Expected {method_name} to be called"

        call_args = method.call_args[0] if method.call_args[0] else method.call_args[1]
        first_arg = call_args[0] if isinstance(call_args, tuple) else call_args

        assert isinstance(
            first_arg, entity_type
        ), f"Expected {entity_type.__name__}, got {type(first_arg)}"

    @staticmethod
    def reset_all_mocks(*mocks: Mock):
        """Reset multiple mock objects."""
        for mock in mocks:
            mock.reset_mock()


# Convenience functions for commonly used patterns
def create_user_repo_mock_with_existing_user(user_data: dict) -> Mock:
    """Create user repository mock that returns an existing user."""
    return UserRepositoryFactory.create_populated_mock(user_data)


def create_user_repo_mock_with_no_users() -> Mock:
    """Create user repository mock that returns no users (empty database)."""
    return UserRepositoryFactory.create_mock_full()


def create_appointment_repo_mock_with_appointments(
    appointments_data: List[dict],
) -> Mock:
    """Create appointment repository mock with multiple appointments."""
    if not IMPORTS_AVAILABLE:
        return Mock()

    mock_repo = AppointmentRepositoryFactory.create_mock_full()

    if appointments_data:
        mock_appointments = [Appointment(**data) for data in appointments_data]
        mock_repo.get_by_user_id.return_value = mock_appointments
        mock_repo.get_by_date_range.return_value = mock_appointments
        mock_repo.get_all.return_value = mock_appointments

    return mock_repo
