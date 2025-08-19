"""
Domain entities - Pure business logic, no framework dependencies.

Following SOLID principles:
- Single Responsibility: Each entity represents one business concept
- Open/Closed: Entities can be extended without modification
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    """Domain entity representing a User in the system.

    This is the pure business representation, independent of:
    - Database implementation (SQLAlchemy)
    - HTTP frameworks (Flask)
    - External services
    """

    id: Optional[int] = None
    email: str = ""
    name: str = ""
    avatar_url: Optional[str] = None
    google_id: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate domain rules."""
        if not self.email:
            raise ValueError("Email is required")
        if not self.name:
            raise ValueError("Name is required")
        if "@" not in self.email:
            raise ValueError("Invalid email format")

        def get_id(self):
            """Return the unique identifier for Flask-Login compatibility."""
            return self.id


@dataclass
class Appointment:
    """Domain entity for Appointment business logic."""

    id: Optional[int] = None
    user_id: int = 0
    service_type: str = ""
    scheduled_date: Optional[datetime] = None
    duration_minutes: int = 0
    price: float = 0.0
    status: str = "scheduled"  # scheduled, confirmed, completed, cancelled
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate business rules."""
        if self.user_id <= 0:
            raise ValueError("Valid user_id is required")
        if not self.service_type:
            raise ValueError("Service type is required")
        if self.duration_minutes <= 0:
            raise ValueError("Duration must be positive")
        if self.price < 0:
            raise ValueError("Price cannot be negative")


@dataclass
class InventoryItem:
    """Domain entity for inventory management."""

    id: Optional[int] = None
    name: str = ""
    category: str = ""
    quantity: int = 0
    unit_price: float = 0.0
    minimum_stock: int = 0
    supplier: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate business rules."""
        if not self.name:
            raise ValueError("Item name is required")
        if self.quantity < 0:
            raise ValueError("Quantity cannot be negative")
        if self.unit_price < 0:
            raise ValueError("Unit price cannot be negative")
        if self.minimum_stock < 0:
            raise ValueError("Minimum stock cannot be negative")

    def is_low_stock(self) -> bool:
        """Business rule: check if item is low on stock."""
        return self.quantity <= self.minimum_stock

    def calculate_total_value(self) -> float:
        """Business rule: calculate total inventory value."""
        return self.quantity * self.unit_price


@dataclass
class Client:
    """Domain entity representing a Client in the system.

    This is the pure business representation, independent of:
    - Database implementation (SQLAlchemy)
    - JotForm API details
    - HTTP frameworks (Flask)
    """

    id: Optional[int] = None
    name: str = ""
    jotform_submission_id: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate domain rules."""
        if not self.name:
            raise ValueError("Client name is required")
        if not self.jotform_submission_id:
            raise ValueError("JotForm submission ID is required")
