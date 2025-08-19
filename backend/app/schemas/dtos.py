"""
Data Transfer Objects (DTOs) and validation schemas.

Following SOLID principles:
- Single Responsibility: Each schema validates one specific data contract
- Open/Closed: Schemas can be extended without modification
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class UserCreateRequest:
    """DTO for user creation requests."""

    email: str
    name: str
    google_id: Optional[str] = None
    avatar_url: Optional[str] = None

    def validate(self) -> None:
        """Validate the request data."""
        if not self.email or "@" not in self.email:
            raise ValueError("Valid email is required")
        if not self.name or len(self.name.strip()) < 2:
            raise ValueError("Name must be at least 2 characters")


@dataclass
class UserUpdateRequest:
    """DTO for user update requests."""

    name: Optional[str] = None
    avatar_url: Optional[str] = None

    def validate(self) -> None:
        """Validate the request data."""
        if self.name is not None and len(self.name.strip()) < 2:
            raise ValueError("Name must be at least 2 characters")


@dataclass
class UserResponse:
    """DTO for user API responses."""

    id: int
    email: str
    name: str
    avatar_url: Optional[str]
    is_active: bool
    created_at: datetime

    @classmethod
    def from_domain(cls, user) -> "UserResponse":
        """Create response from domain entity."""
        return cls(
            id=user.id,
            email=user.email,
            name=user.name,
            avatar_url=user.avatar_url,
            is_active=user.is_active,
            created_at=user.created_at or datetime.now(),
        )


@dataclass
class AppointmentCreateRequest:
    """DTO for appointment creation requests."""

    user_id: int
    service_type: str
    scheduled_date: datetime
    duration_minutes: int
    price: float
    notes: Optional[str] = None

    def validate(self) -> None:
        """Validate the request data."""
        if self.user_id <= 0:
            raise ValueError("Valid user_id is required")
        if not self.service_type:
            raise ValueError("Service type is required")
        if self.duration_minutes <= 0:
            raise ValueError("Duration must be positive")
        if self.price < 0:
            raise ValueError("Price cannot be negative")
        if self.scheduled_date <= datetime.now():
            raise ValueError("Appointment must be scheduled for future date")


@dataclass
class AppointmentUpdateRequest:
    """DTO for appointment update requests."""

    scheduled_date: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    price: Optional[float] = None
    status: Optional[str] = None
    notes: Optional[str] = None

    def validate(self) -> None:
        """Validate the request data."""
        if self.duration_minutes is not None and self.duration_minutes <= 0:
            raise ValueError("Duration must be positive")
        if self.price is not None and self.price < 0:
            raise ValueError("Price cannot be negative")
        if self.status is not None and self.status not in [
            "scheduled",
            "confirmed",
            "completed",
            "cancelled",
        ]:
            raise ValueError("Invalid status")


@dataclass
class AppointmentResponse:
    """DTO for appointment API responses."""

    id: int
    user_id: int
    service_type: str
    scheduled_date: datetime
    duration_minutes: int
    price: float
    status: str
    notes: Optional[str]
    created_at: datetime

    @classmethod
    def from_domain(cls, appointment) -> "AppointmentResponse":
        """Create response from domain entity."""
        return cls(
            id=appointment.id,
            user_id=appointment.user_id,
            service_type=appointment.service_type,
            scheduled_date=appointment.scheduled_date,
            duration_minutes=appointment.duration_minutes,
            price=appointment.price,
            status=appointment.status,
            notes=appointment.notes,
            created_at=appointment.created_at or datetime.now(),
        )


@dataclass
class InventoryItemCreateRequest:
    """DTO for inventory item creation requests."""

    name: str
    category: str
    quantity: int
    unit_price: float
    minimum_stock: int
    supplier: Optional[str] = None

    def validate(self) -> None:
        """Validate the request data."""
        if not self.name:
            raise ValueError("Item name is required")
        if not self.category:
            raise ValueError("Category is required")
        if self.quantity < 0:
            raise ValueError("Quantity cannot be negative")
        if self.unit_price < 0:
            raise ValueError("Unit price cannot be negative")
        if self.minimum_stock < 0:
            raise ValueError("Minimum stock cannot be negative")


@dataclass
class InventoryItemUpdateRequest:
    """DTO for inventory item update requests."""

    name: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[int] = None
    unit_price: Optional[float] = None
    minimum_stock: Optional[int] = None
    supplier: Optional[str] = None

    def validate(self) -> None:
        """Validate the request data."""
        if self.quantity is not None and self.quantity < 0:
            raise ValueError("Quantity cannot be negative")
        if self.unit_price is not None and self.unit_price < 0:
            raise ValueError("Unit price cannot be negative")
        if self.minimum_stock is not None and self.minimum_stock < 0:
            raise ValueError("Minimum stock cannot be negative")


@dataclass
class InventoryItemResponse:
    """DTO for inventory item API responses."""

    id: int
    name: str
    category: str
    quantity: int
    unit_price: float
    minimum_stock: int
    supplier: Optional[str]
    total_value: float
    is_low_stock: bool
    created_at: datetime

    @classmethod
    def from_domain(cls, item) -> "InventoryItemResponse":
        """Create response from domain entity."""
        return cls(
            id=item.id,
            name=item.name,
            category=item.category,
            quantity=item.quantity,
            unit_price=item.unit_price,
            minimum_stock=item.minimum_stock,
            supplier=item.supplier,
            total_value=item.calculate_total_value(),
            is_low_stock=item.is_low_stock(),
            created_at=item.created_at or datetime.now(),
        )


@dataclass
class AuthTokenResponse:
    """DTO for authentication token responses."""

    token: str
    user: UserResponse
    expires_in: int  # seconds

    @classmethod
    def create(cls, token: str, user, expires_in: int = 86400) -> "AuthTokenResponse":
        """Create auth response."""
        return cls(
            token=token, user=UserResponse.from_domain(user), expires_in=expires_in
        )


@dataclass
class ErrorResponse:
    """DTO for error responses."""

    error: str
    message: str
    details: Optional[dict] = None

    @classmethod
    def validation_error(
        cls, message: str, details: Optional[dict] = None
    ) -> "ErrorResponse":
        """Create validation error response."""
        return cls(error="validation_error", message=message, details=details)

    @classmethod
    def not_found(cls, resource: str) -> "ErrorResponse":
        """Create not found error response."""
        return cls(error="not_found", message=f"{resource} not found")

    @classmethod
    def server_error(cls, message: str = "Internal server error") -> "ErrorResponse":
        """Create server error response."""
        return cls(error="server_error", message=message)
