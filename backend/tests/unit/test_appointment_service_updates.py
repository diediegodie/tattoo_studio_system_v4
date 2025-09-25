"""
Unit tests for AppointmentService update functionality.

This module tests appointment update operations:
- Successful appointment updates
- Error handling when appointment doesn't exist
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
    """Initialize AppointmentService with mocked repositories."""
    return AppointmentService(mock_appointment_repo, mock_user_repo)


@pytest.mark.unit
@pytest.mark.services
@pytest.mark.appointment
class TestAppointmentServiceUpdates:
    """Test appointment update functionality."""

    def test_update_appointment_success(self, service, mock_appointment_repo):
        """Test successful appointment update."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        appointment_id = 1
        existing_appointment = DomainAppointment(
            id=appointment_id,
            user_id=1,
            service_type="tattoo",
            scheduled_date=datetime.now() + timedelta(days=1),
            duration_minutes=60,
            price=150.0,
            status="scheduled",
        )
        mock_appointment_repo.get_by_id.return_value = existing_appointment

        updated_appointment = DomainAppointment(
            id=appointment_id,
            user_id=1,
            service_type="tattoo",
            scheduled_date=datetime.now() + timedelta(days=2),
            duration_minutes=90,
            price=200.0,
            status="scheduled",
        )
        mock_appointment_repo.update.return_value = updated_appointment

        request = AppointmentUpdateRequest(
            scheduled_date=datetime.now() + timedelta(days=2),
            duration_minutes=90,
            price=200.0,
        )

        result = service.update_appointment(appointment_id, request)

        assert isinstance(result, AppointmentResponse)
        assert result.scheduled_date == updated_appointment.scheduled_date
        assert result.duration_minutes == 90
        assert result.price == 200.0
        mock_appointment_repo.get_by_id.assert_called_once_with(appointment_id)
        mock_appointment_repo.update.assert_called_once()

    def test_update_appointment_not_found(self, service, mock_appointment_repo):
        """Test appointment update when appointment doesn't exist."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        appointment_id = 999
        mock_appointment_repo.get_by_id.return_value = None

        request = AppointmentUpdateRequest(price=200.0)

        result = service.update_appointment(appointment_id, request)

        assert result is None
        mock_appointment_repo.get_by_id.assert_called_once_with(appointment_id)
        mock_appointment_repo.update.assert_not_called()
