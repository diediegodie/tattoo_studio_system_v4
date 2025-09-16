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

# Import all test classes from split modules
from .test_appointment_service_creation import TestAppointmentServiceCreation
from .test_appointment_service_updates import TestAppointmentServiceUpdates
from .test_appointment_service_queries import TestAppointmentServiceQueries
from .test_appointment_service_cancellation import TestAppointmentServiceCancellation
from .test_appointment_service_status import TestAppointmentServiceStatusChanges
from .test_appointment_service_schedule import TestAppointmentServiceSchedule

# Re-export all test classes for pytest discovery
__all__ = [
    "TestAppointmentServiceCreation",
    "TestAppointmentServiceUpdates",
    "TestAppointmentServiceQueries",
    "TestAppointmentServiceCancellation",
    "TestAppointmentServiceStatusChanges",
    "TestAppointmentServiceSchedule",
]
