"""
Unit tests for AppointmentService cancellation functionality.

This module tests appointment cancellation operations:
- Successful appointment cancellation
- Error handling when appointment doesn't exist
- Error handling when trying to cancel completed appointments
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
class TestAppointmentServiceCancellation:
    """Test appointment cancellation functionality."""

    def test_cancel_appointment_success(self, service, mock_appointment_repo):
        """Test successful appointment cancellation."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        appointment_id = 1
        appointment = DomainAppointment(
            id=appointment_id,
            user_id=1,
            service_type="tattoo",
            scheduled_date=datetime.now() + timedelta(days=2),
            duration_minutes=60,
            price=150.0,
            status="scheduled",
        )
        mock_appointment_repo.get_by_id.return_value = appointment
        mock_appointment_repo.cancel.return_value = True

        result = service.cancel_appointment(appointment_id)

        assert result is True
        mock_appointment_repo.get_by_id.assert_called_once_with(appointment_id)
        mock_appointment_repo.cancel.assert_called_once_with(appointment_id)

    def test_cancel_appointment_not_found(self, service, mock_appointment_repo):
        """Test cancellation when appointment doesn't exist."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        appointment_id = 999
        mock_appointment_repo.get_by_id.return_value = None

        result = service.cancel_appointment(appointment_id)

        assert result is False
        mock_appointment_repo.get_by_id.assert_called_once_with(appointment_id)
        mock_appointment_repo.cancel.assert_not_called()

    def test_cancel_appointment_completed(self, service, mock_appointment_repo):
        """Test cancellation of completed appointment."""
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
            status="completed",
        )
        mock_appointment_repo.get_by_id.return_value = appointment

        with pytest.raises(ValueError, match="Cannot cancel completed appointment"):
            service.cancel_appointment(appointment_id)

        mock_appointment_repo.cancel.assert_not_called()
