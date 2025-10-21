"""
Appointment service following SOLID principles.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from app.domain.entities import Appointment as DomainAppointment
from app.domain.interfaces import IAppointmentRepository, IUserRepository
from app.schemas.dtos import (
    AppointmentCreateRequest,
    AppointmentResponse,
    AppointmentUpdateRequest,
)


class AppointmentService:
    """Application service for appointment-related use-cases.

    This service demonstrates:
    - Single Responsibility: Handles only appointment business logic
    - Dependency Inversion: Depends on interfaces, not concrete implementations
    - Open/Closed: Can be extended without modification
    """

    def __init__(
        self, appointment_repo: IAppointmentRepository, user_repo: IUserRepository
    ):
        self.appointment_repo = appointment_repo
        self.user_repo = user_repo

    def create_appointment(
        self, request: AppointmentCreateRequest
    ) -> AppointmentResponse:
        """Create a new appointment with business rule validation.

        Business Rules:
        - User must exist and be active
        - Appointment must be in the future
        - No double booking for the same time slot
        """
        # Validate request
        request.validate()

        # Verify user exists and is active
        user = self.user_repo.get_by_id(request.user_id)
        if not user:
            raise ValueError("User not found")
        if not user.is_active:
            raise ValueError("User account is inactive")

        # Verify no conflicting appointments (business rule)
        if self._has_conflicting_appointment(
            request.scheduled_date, request.duration_minutes
        ):
            raise ValueError("Time slot is already booked")

        # Create domain entity
        appointment = DomainAppointment(
            user_id=request.user_id,
            service_type=request.service_type,
            scheduled_date=request.scheduled_date,
            duration_minutes=request.duration_minutes,
            price=request.price,
            notes=request.notes,
            status="scheduled",
        )

        # Save through repository
        created_appointment = self.appointment_repo.create(appointment)

        return AppointmentResponse.from_domain(created_appointment)

    def update_appointment(
        self, appointment_id: int, request: AppointmentUpdateRequest
    ) -> Optional[AppointmentResponse]:
        """Update an existing appointment."""
        # Validate request
        request.validate()

        # Get existing appointment
        appointment = self.appointment_repo.get_by_id(appointment_id)
        if not appointment:
            return None

        # Apply updates
        if request.scheduled_date:
            appointment.scheduled_date = request.scheduled_date
        if request.duration_minutes:
            appointment.duration_minutes = request.duration_minutes
        if request.price is not None:
            appointment.price = request.price
        if request.status:
            appointment.status = request.status
        if request.notes is not None:
            appointment.notes = request.notes

        # Save changes
        updated_appointment = self.appointment_repo.update(appointment)

        return AppointmentResponse.from_domain(updated_appointment)

    def get_appointments_for_user(self, user_id: int) -> List[AppointmentResponse]:
        """Get all appointments for a specific user."""
        appointments = self.appointment_repo.get_by_user_id(user_id)
        return [AppointmentResponse.from_domain(apt) for apt in appointments]

    def get_appointments_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> List[AppointmentResponse]:
        """Get appointments within a date range."""
        appointments = self.appointment_repo.get_by_date_range(start_date, end_date)
        return [AppointmentResponse.from_domain(apt) for apt in appointments]

    def cancel_appointment(
        self, appointment_id: int, reason: Optional[str] = None
    ) -> bool:
        """Cancel an appointment with business rules."""
        appointment = self.appointment_repo.get_by_id(appointment_id)
        if not appointment:
            return False

        # Business rule: Can't cancel appointments that are already completed
        if appointment.status == "completed":
            raise ValueError("Cannot cancel completed appointment")

        # Business rule: Add cancellation notice if within 24 hours
        if (
            appointment.scheduled_date
            and appointment.scheduled_date <= datetime.now() + timedelta(hours=24)
        ):
            # Could trigger notification, late cancellation fee, etc.
            pass

        return self.appointment_repo.cancel(appointment_id)

    def confirm_appointment(self, appointment_id: int) -> bool:
        """Confirm an appointment (change status from scheduled to confirmed)."""
        appointment = self.appointment_repo.get_by_id(appointment_id)
        if not appointment:
            return False

        if appointment.status != "scheduled":
            raise ValueError("Only scheduled appointments can be confirmed")

        appointment.status = "confirmed"
        self.appointment_repo.update(appointment)
        return True

    def complete_appointment(
        self, appointment_id: int, notes: Optional[str] = None
    ) -> bool:
        """Mark an appointment as completed."""
        appointment = self.appointment_repo.get_by_id(appointment_id)
        if not appointment:
            return False

        if appointment.status not in ["scheduled", "confirmed"]:
            raise ValueError(
                "Only scheduled or confirmed appointments can be completed"
            )

        appointment.status = "completed"
        if notes:
            appointment.notes = (
                f"{appointment.notes}\n{notes}" if appointment.notes else notes
            )

        self.appointment_repo.update(appointment)
        return True

    def _has_conflicting_appointment(
        self, scheduled_date: datetime, duration_minutes: int
    ) -> bool:
        """Check if there's a conflicting appointment at the given time.

        Business rule: No overlapping appointments.
        """
        if not scheduled_date:
            return False

        # Calculate the end time of the proposed appointment
        end_date = scheduled_date + timedelta(minutes=duration_minutes)

        # Get all appointments in the date range
        existing_appointments = self.appointment_repo.get_by_date_range(
            scheduled_date, end_date
        )

        # Check for any overlapping appointments
        for appointment in existing_appointments or []:
            if not appointment or not appointment.scheduled_date:
                continue

            if appointment.status == "cancelled":
                continue  # Skip cancelled appointments

            appointment_end = appointment.scheduled_date + timedelta(
                minutes=appointment.duration_minutes or 0
            )

            # Check for overlap
            if (
                scheduled_date < appointment_end
                and end_date > appointment.scheduled_date
            ):
                return True

        return False

    def get_daily_schedule(self, date: datetime) -> List[AppointmentResponse]:
        """Get all appointments for a specific day."""
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)

        return self.get_appointments_by_date_range(start_of_day, end_of_day)

    def get_available_time_slots(
        self, date: datetime, duration_minutes: int
    ) -> List[datetime]:
        """Get available time slots for a given date and duration.

        Business logic for scheduling optimization.
        """
        # This would implement complex scheduling logic
        # For now, return empty list as the repository is not fully implemented
        return []
