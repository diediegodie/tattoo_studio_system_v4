"""
Abstract interfaces for repositories following Interface Segregation Principle.

These interfaces define contracts without implementation details,
enabling dependency injection and easier testing.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from domain.entities import User, Appointment, InventoryItem


class IUserReader(ABC):
    """Interface for user read operations - Interface Segregation Principle."""

    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        pass

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        pass

    @abstractmethod
    def get_by_google_id(self, google_id: str) -> Optional[User]:
        """Get user by Google ID."""
        pass


class IUserWriter(ABC):
    """Interface for user write operations - Interface Segregation Principle."""

    @abstractmethod
    def create(self, user: User) -> User:
        """Create a new user."""
        pass

    @abstractmethod
    def update(self, user: User) -> User:
        """Update an existing user."""
        pass

    @abstractmethod
    def delete(self, user_id: int) -> bool:
        """Delete a user."""
        pass


class IUserRepository(IUserReader, IUserWriter):
    """Complete user repository interface combining read/write operations."""

    pass


class IAppointmentReader(ABC):
    """Interface for appointment read operations."""

    @abstractmethod
    def get_by_id(self, appointment_id: int) -> Optional[Appointment]:
        """Get appointment by ID."""
        pass

    @abstractmethod
    def get_by_user_id(self, user_id: int) -> List[Appointment]:
        """Get all appointments for a user."""
        pass

    @abstractmethod
    def get_by_date_range(self, start_date, end_date) -> List[Appointment]:
        """Get appointments in date range."""
        pass


class IAppointmentWriter(ABC):
    """Interface for appointment write operations."""

    @abstractmethod
    def create(self, appointment: Appointment) -> Appointment:
        """Create a new appointment."""
        pass

    @abstractmethod
    def update(self, appointment: Appointment) -> Appointment:
        """Update an existing appointment."""
        pass

    @abstractmethod
    def cancel(self, appointment_id: int) -> bool:
        """Cancel an appointment."""
        pass


class IAppointmentRepository(IAppointmentReader, IAppointmentWriter):
    """Complete appointment repository interface."""

    pass


class IInventoryReader(ABC):
    """Interface for inventory read operations."""

    @abstractmethod
    def get_by_id(self, item_id: int) -> Optional[InventoryItem]:
        """Get inventory item by ID."""
        pass

    @abstractmethod
    def get_all(self) -> List[InventoryItem]:
        """Get all inventory items."""
        pass

    @abstractmethod
    def get_low_stock_items(self) -> List[InventoryItem]:
        """Get items with low stock."""
        pass

    @abstractmethod
    def search_by_name(self, name: str) -> List[InventoryItem]:
        """Search items by name."""
        pass


class IInventoryWriter(ABC):
    """Interface for inventory write operations."""

    @abstractmethod
    def create(self, item: InventoryItem) -> InventoryItem:
        """Create a new inventory item."""
        pass

    @abstractmethod
    def update(self, item: InventoryItem) -> InventoryItem:
        """Update an existing inventory item."""
        pass

    @abstractmethod
    def delete(self, item_id: int) -> bool:
        """Delete an inventory item."""
        pass

    @abstractmethod
    def update_stock(self, item_id: int, quantity_change: int) -> bool:
        """Update stock quantity (positive = add, negative = remove)."""
        pass


class IInventoryRepository(IInventoryReader, IInventoryWriter):
    """Complete inventory repository interface."""

    pass
