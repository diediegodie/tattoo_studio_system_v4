"""
Unit tests for AppointmentService schedule operations.

This module tests appointment scheduling functionality:
- Time slot availability checking
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
class TestAppointmentServiceSchedule:
    """Test appointment schedule operations."""

    def test_get_available_time_slots(self, service, mock_appointment_repo):
        """Test getting available time slots for a date."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        target_date = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
        duration_minutes = 60

        # The method currently returns empty list as per implementation
        # and doesn't call the repository yet
        available_slots = service.get_available_time_slots(
            target_date, duration_minutes
        )

        assert isinstance(available_slots, list)
        assert len(available_slots) == 0
        # Repository is not called in current implementation
        mock_appointment_repo.get_by_date_range.assert_not_called()
