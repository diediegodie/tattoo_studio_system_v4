"""
Unit tests for AppointmentService query functionality.

This module tests appointment query operations:
- Getting appointments for a specific user
- Getting appointments by date range
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
    from app.schemas.dtos import (
        AppointmentCreateRequest,
        AppointmentResponse,
        AppointmentUpdateRequest,
    )
    from app.services.appointment_service import AppointmentService
    from tests.factories.repository_factories import (
        AppointmentRepositoryFactory,
        UserRepositoryFactory,
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
class TestAppointmentServiceQueries:
    """Test appointment query functionality."""

    def test_get_appointments_for_user_success(self, service, mock_appointment_repo):
        """Test successful retrieval of user appointments."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        user_id = 1
        appointments = [
            DomainAppointment(
                id=1,
                user_id=user_id,
                service_type="tattoo",
                scheduled_date=datetime.now() + timedelta(days=1),
                duration_minutes=60,
                price=150.0,
                status="scheduled",
            ),
            DomainAppointment(
                id=2,
                user_id=user_id,
                service_type="piercing",
                scheduled_date=datetime.now() + timedelta(days=2),
                duration_minutes=30,
                price=50.0,
                status="confirmed",
            ),
        ]
        mock_appointment_repo.get_by_user_id.return_value = appointments

        result = service.get_appointments_for_user(user_id)

        assert len(result) == 2
        assert all(isinstance(apt, AppointmentResponse) for apt in result)
        assert result[0].service_type == "tattoo"
        assert result[1].service_type == "piercing"
        mock_appointment_repo.get_by_user_id.assert_called_once_with(user_id)

    def test_get_appointments_by_date_range_success(
        self, service, mock_appointment_repo
    ):
        """Test successful retrieval of appointments by date range."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        start_date = datetime.now()
        end_date = start_date + timedelta(days=7)

        appointments = [
            DomainAppointment(
                id=1,
                user_id=1,
                service_type="tattoo",
                scheduled_date=start_date + timedelta(days=1),
                duration_minutes=60,
                price=150.0,
                status="scheduled",
            )
        ]
        mock_appointment_repo.get_by_date_range.return_value = appointments

        result = service.get_appointments_by_date_range(start_date, end_date)

        assert len(result) == 1
        assert isinstance(result[0], AppointmentResponse)
        mock_appointment_repo.get_by_date_range.assert_called_once_with(
            start_date, end_date
        )
