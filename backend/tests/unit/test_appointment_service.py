"""
Unit tests for AppointmentService following SOLID principles and existing test patterns.

This module tests the AppointmentService business logic with comprehensive coverage:
- Appointment creation with validation
- Appointment updates and status changes
- User and date range queries
- Cancellation and completion business rules
- Error handling and edge cases
"""

import pytest
from unittest.mock import Mock
from datetime import datetime, timedelta

# Test configuration and imports
from tests.config.test_paths import ensure_domain_imports

ensure_domain_imports()

try:
    from services.appointment_service import AppointmentService
    from tests.factories.repository_factories import (
        AppointmentRepositoryFactory,
        UserRepositoryFactory,
    )
    from domain.entities import Appointment as DomainAppointment, User
    from schemas.dtos import (
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
    return AppointmentRepositoryFactory.create_mock_full()


@pytest.fixture
def mock_user_repo() -> Mock:
    """Create a mock user repository."""
    return UserRepositoryFactory.create_mock_full()


@pytest.fixture
def service(mock_appointment_repo, mock_user_repo) -> AppointmentService:
    """Initialize AppointmentService with mocked dependencies."""
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


@pytest.mark.unit
@pytest.mark.services
@pytest.mark.appointment
class TestAppointmentServiceSchedule:
    """Test appointment scheduling functionality."""

    def test_get_daily_schedule_success(self, service, mock_appointment_repo):
        """Test successful retrieval of daily schedule."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        date = datetime.now()
        appointments = [
            DomainAppointment(
                id=1,
                user_id=1,
                service_type="tattoo",
                scheduled_date=date.replace(hour=10, minute=0),
                duration_minutes=60,
                price=150.0,
                status="scheduled",
            )
        ]
        mock_appointment_repo.get_by_date_range.return_value = appointments

        result = service.get_daily_schedule(date)

        assert len(result) == 1
        assert isinstance(result[0], AppointmentResponse)
        mock_appointment_repo.get_by_date_range.assert_called_once()

    def test_get_available_time_slots_empty(self, service, mock_appointment_repo):
        """Test retrieval of available time slots (currently returns empty)."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        date = datetime.now()
        result = service.get_available_time_slots(date, 60)

        assert result == []
        # Note: This method currently returns empty list as per implementation
