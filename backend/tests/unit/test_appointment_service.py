"""
Unit tests for AppointmentService - Main module importing from split test files.

This module serves as the main entry point for AppointmentService tests.
All test classes have been split into separate modules for better maintainability:

- test_appointment_service_creation.py: Appointment creation tests
- test_appointment_service_updates.py: Appointment update tests
- test_appointment_service_queries.py: Appointment query tests
- test_appointment_service_cancellation.py: Appointment cancellation tests
- test_appointment_service_status.py: Appointment status change tests
- test_appointment_service_schedule.py: Appointment schedule tests

This file imports all test classes to maintain backward compatibility.
"""

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


from .test_appointment_service_cancellation import TestAppointmentServiceCancellation

# Import all test classes from split modules
from .test_appointment_service_creation import TestAppointmentServiceCreation
from .test_appointment_service_queries import TestAppointmentServiceQueries
from .test_appointment_service_schedule import TestAppointmentServiceSchedule
from .test_appointment_service_status import TestAppointmentServiceStatusChanges
from .test_appointment_service_updates import TestAppointmentServiceUpdates

# Re-export all test classes for pytest discovery
__all__ = [
    "TestAppointmentServiceCreation",
    "TestAppointmentServiceUpdates",
    "TestAppointmentServiceQueries",
    "TestAppointmentServiceCancellation",
    "TestAppointmentServiceStatusChanges",
    "TestAppointmentServiceSchedule",
]
