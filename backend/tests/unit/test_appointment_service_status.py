"""
Unit tests for AppointmentService status change operations.

This module tests appointment status change functionality:
- Appointment confirmation
- Appointment completion
- Error handling for invalid status transitions
"""

import pytest
from unittest.mock import Mock
from datetime import datetime, timedelta

# Test configuration and imports
from tests.config.test_paths import ensure_domain_imports

ensure_domain_imports()

try:
    from app.services.appointment_service import AppointmentService
    from tests.factories.repository_factories import (
        AppointmentRepositoryFactory,
        UserRepositoryFactory,
    )
    from app.domain.entities import Appointment as DomainAppointment, User
    from app.schemas.dtos import (
        AppointmentCreateRequest,
        AppointmentUpdateRequest,
        AppointmentResponse,
    )

    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import required modules: {e}")
    IMPORTS_AVAILABLE = False


@pytest.fixture
def mock_appointment_repo() -> Mock:
    """Create a mock appointment repository."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Required modules not available")
    return AppointmentRepositoryFactory.create_mock_full()


@pytest.fixture
def mock_user_repo() -> Mock:
    """Create a mock user repository."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Required modules not available")
    return UserRepositoryFactory.create_mock_full()


@pytest.fixture
def service(mock_appointment_repo, mock_user_repo) -> "AppointmentService":
    """Initialize AppointmentService with mocked repositories."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Required modules not available")
    return AppointmentService(mock_appointment_repo, mock_user_repo)


@pytest.mark.unit
@pytest.mark.services
@pytest.mark.appointment
class TestAppointmentServiceStatusChanges:
    """Test appointment status change operations."""

    def test_confirm_appointment_success(self, service, mock_appointment_repo):
        """Test successful appointment confirmation."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        appointment_id = 1
        appointment = DomainAppointment(
            id=appointment_id,
            user_id=1,
            service_type="tattoo",
            scheduled_date=datetime.now() + timedelta(days=1),
            duration_minutes=60,
            price=150.0,
            status="scheduled",
        )
        mock_appointment_repo.get_by_id.return_value = appointment

        result = service.confirm_appointment(appointment_id)

        assert result is True
        assert appointment.status == "confirmed"
        mock_appointment_repo.get_by_id.assert_called_once_with(appointment_id)
        mock_appointment_repo.update.assert_called_once_with(appointment)

    def test_confirm_appointment_not_scheduled(self, service, mock_appointment_repo):
        """Test confirmation of non-scheduled appointment."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        appointment_id = 1
        appointment = DomainAppointment(
            id=appointment_id,
            user_id=1,
            service_type="tattoo",
            scheduled_date=datetime.now() + timedelta(days=1),
            duration_minutes=60,
            price=150.0,
            status="confirmed",
        )
        mock_appointment_repo.get_by_id.return_value = appointment

        with pytest.raises(
            ValueError, match="Only scheduled appointments can be confirmed"
        ):
            service.confirm_appointment(appointment_id)

    def test_complete_appointment_success(self, service, mock_appointment_repo):
        """Test successful appointment completion."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        appointment_id = 1
        appointment = DomainAppointment(
            id=appointment_id,
            user_id=1,
            service_type="tattoo",
            scheduled_date=datetime.now() + timedelta(days=1),
            duration_minutes=60,
            price=150.0,
            status="confirmed",
            notes="Initial notes",
        )
        mock_appointment_repo.get_by_id.return_value = appointment

        result = service.complete_appointment(
            appointment_id, "Work completed successfully"
        )

        assert result is True
        assert appointment.status == "completed"
        assert "Work completed successfully" in appointment.notes
        mock_appointment_repo.get_by_id.assert_called_once_with(appointment_id)
        mock_appointment_repo.update.assert_called_once_with(appointment)

    def test_complete_appointment_invalid_status(self, service, mock_appointment_repo):
        """Test completion of appointment with invalid status."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        appointment_id = 1
        appointment = DomainAppointment(
            id=appointment_id,
            user_id=1,
            service_type="tattoo",
            scheduled_date=datetime.now() + timedelta(days=1),
            duration_minutes=60,
            price=150.0,
            status="cancelled",
        )
        mock_appointment_repo.get_by_id.return_value = appointment

        with pytest.raises(
            ValueError,
            match="Only scheduled or confirmed appointments can be completed",
        ):
            service.complete_appointment(appointment_id)
