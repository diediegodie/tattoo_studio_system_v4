"""
Unit tests for AppointmentService creation functionality.

This module tests appointment creation operations:
- Successful appointment creation with validation
- Error handling when user doesn't exist
- Error handling when user is inactive
- Conflict detection for time slots
"""

from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest
# Test configuration and imports
from tests.config.test_paths import ensure_domain_imports

ensure_domain_imports()

try:
    from app.domain.entities import Appointment as DomainAppointment
    from app.domain.entities import User
    from app.schemas.dtos import (AppointmentCreateRequest,
                                  AppointmentResponse,
                                  AppointmentUpdateRequest)
    from app.services.appointment_service import AppointmentService
    from tests.factories.repository_factories import (
        AppointmentRepositoryFactory, UserRepositoryFactory)

    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import required modules: {e}")
    IMPORTS_AVAILABLE = False


@pytest.fixture
def mock_appointment_repo() -> Mock:
    """Create a mock appointment repository."""
    return AppointmentRepositoryFactory.create_mock_full()


@pytest.fixture
def mock_user_repo() -> Mock:
    """Create a mock user repository."""
    return UserRepositoryFactory.create_mock_full()


@pytest.fixture
def service(mock_appointment_repo, mock_user_repo) -> "AppointmentService":
    """Initialize AppointmentService with mocked repositories."""
    return AppointmentService(mock_appointment_repo, mock_user_repo)


@pytest.mark.unit
@pytest.mark.services
@pytest.mark.appointment
class TestAppointmentServiceCreation:
    """Test appointment creation functionality."""

    def test_create_appointment_success(
        self, service, mock_appointment_repo, mock_user_repo
    ):
        """Test successful appointment creation."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock user exists
        user = User(id=1, email="user@example.com", name="Test User", is_active=True)
        mock_user_repo.get_by_id.return_value = user

        # Mock no conflicting appointments
        mock_appointment_repo.get_by_date_range.return_value = []

        # Mock creation
        created_appointment = DomainAppointment(
            id=1,
            user_id=1,
            service_type="tattoo",
            scheduled_date=datetime.now() + timedelta(days=1),
            duration_minutes=60,
            price=150.0,
            status="scheduled",
        )
        mock_appointment_repo.create.return_value = created_appointment

        request = AppointmentCreateRequest(
            user_id=1,
            service_type="tattoo",
            scheduled_date=datetime.now() + timedelta(days=1),
            duration_minutes=60,
            price=150.0,
        )

        result = service.create_appointment(request)

        assert isinstance(result, AppointmentResponse)
        assert result.user_id == 1
        assert result.service_type == "tattoo"
        assert result.status == "scheduled"
        mock_user_repo.get_by_id.assert_called_once_with(1)
        mock_appointment_repo.create.assert_called_once()

    def test_create_appointment_user_not_found(self, service, mock_user_repo):
        """Test appointment creation when user doesn't exist."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        mock_user_repo.get_by_id.return_value = None

        request = AppointmentCreateRequest(
            user_id=999,
            service_type="tattoo",
            scheduled_date=datetime.now() + timedelta(days=1),
            duration_minutes=60,
            price=150.0,
        )

        with pytest.raises(ValueError, match="User not found"):
            service.create_appointment(request)

    def test_create_appointment_user_inactive(self, service, mock_user_repo):
        """Test appointment creation when user is inactive."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock inactive user
        user = User(id=1, email="user@example.com", name="Test User", is_active=False)
        mock_user_repo.get_by_id.return_value = user

        request = AppointmentCreateRequest(
            user_id=1,
            service_type="tattoo",
            scheduled_date=datetime.now() + timedelta(days=1),
            duration_minutes=60,
            price=150.0,
        )

        with pytest.raises(ValueError, match="User account is inactive"):
            service.create_appointment(request)

    def test_create_appointment_conflicting_time_slot(
        self, service, mock_appointment_repo, mock_user_repo
    ):
        """Test appointment creation with conflicting time slot."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock user exists
        user = User(id=1, email="user@example.com", name="Test User", is_active=True)
        mock_user_repo.get_by_id.return_value = user

        # Mock conflicting appointment exists
        conflicting_appointment = DomainAppointment(
            id=2,
            user_id=2,
            service_type="tattoo",
            scheduled_date=datetime.now() + timedelta(days=1),
            duration_minutes=60,
            price=150.0,
            status="scheduled",
        )
        mock_appointment_repo.get_by_date_range.return_value = [conflicting_appointment]

        request = AppointmentCreateRequest(
            user_id=1,
            service_type="tattoo",
            scheduled_date=datetime.now() + timedelta(days=1),
            duration_minutes=60,
            price=150.0,
        )

        with pytest.raises(ValueError, match="Time slot is already booked"):
            service.create_appointment(request)
