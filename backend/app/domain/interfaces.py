"""
Abstract interfaces for repositories following Interface Segregation Principle.

These interfaces define contracts without implementation details,
enabling dependency injection and easier testing.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from .entities import Appointment, CalendarEvent, Client, InventoryItem, User


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

    @abstractmethod
    def get_all_artists(self) -> List[User]:
        """Get all users with role 'artist'."""
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

    @abstractmethod
    def get_related_sessions_count(self, user_id: int) -> int:
        """Get count of sessions related to a user."""
        pass

    @abstractmethod
    def get_related_payments_count(self, user_id: int) -> int:
        """Get count of payments related to a user."""
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


class IClientReader(ABC):
    """Interface for client read operations - Interface Segregation Principle."""

    @abstractmethod
    def get_by_id(self, client_id: int) -> Optional[Client]:
        """Get client by ID."""
        pass

    @abstractmethod
    def get_all(self) -> List[Client]:
        """Get all clients."""
        pass

    @abstractmethod
    def get_by_jotform_id(self, jotform_id: str) -> Optional[Client]:
        """Retrieve a client by their JotForm submission ID."""
        pass

    @abstractmethod
    def get_all_by_jotform_ids(self, jotform_ids: List[str]) -> dict[str, Client]:
        """Batch retrieve clients by JotForm IDs. Returns map of jotform_id -> Client."""
        pass

    @abstractmethod
    def batch_create_and_update(
        self, clients_to_create: List[Client], clients_to_update: List[Client]
    ) -> List[Client]:
        """Batch create and update clients with single commit."""
        pass


class IClientWriter(ABC):
    """Interface for client write operations - Interface Segregation Principle."""

    @abstractmethod
    def create(self, client: Client) -> Client:
        """Create a new client."""
        pass

    @abstractmethod
    def update(self, client: Client) -> Client:
        """Update an existing client."""
        pass

    @abstractmethod
    def delete(self, client_id: int) -> bool:
        """Delete a client."""
        pass


class IClientRepository(IClientReader, IClientWriter):
    """Complete client repository interface combining read/write operations."""

    pass


class IJotFormService(ABC):
    """Interface for JotForm API integration."""

    @abstractmethod
    def fetch_submissions(self) -> List[dict]:
        """Fetch all active submissions from JotForm."""
        pass

    @abstractmethod
    def parse_client_name(self, submission: dict) -> str:
        """Parse client name from JotForm submission."""
        pass

    @abstractmethod
    def format_submission_data(self, submission: dict) -> dict:
        """Format submission data for display."""
        pass


class ICalendarService(ABC):
    """
    Interface for calendar operations.
    Follows Interface Segregation Principle - focused on calendar concerns only.
    """

    @abstractmethod
    def get_user_events(
        self, user_id: str, start_date: datetime, end_date: datetime
    ) -> List[CalendarEvent]:
        """Get user's calendar events within date range."""
        pass

    @abstractmethod
    def sync_events_with_sessions(self, user_id: str) -> bool:
        """Sync Google Calendar events with local sessions."""
        pass

    @abstractmethod
    def create_session_event(
        self, session_id: str, event_details: CalendarEvent
    ) -> Optional[str]:
        """Create a calendar event for a session."""
        pass

    @abstractmethod
    def is_user_authorized(self, user_id: str) -> bool:
        """Check if user has authorized calendar access."""
        pass


class IGoogleCalendarRepository(ABC):
    """
    Interface for Google Calendar API operations.
    Follows Interface Segregation Principle - focused on external API access.
    """

    @abstractmethod
    def fetch_events(
        self, access_token: str, start_date: datetime, end_date: datetime
    ) -> List[dict]:
        """Fetch events from Google Calendar API."""
        pass

    @abstractmethod
    def create_event(self, access_token: str, event_data: dict) -> Optional[str]:
        """Create an event in Google Calendar."""
        pass

    @abstractmethod
    def validate_token(self, access_token: str) -> bool:
        """Validate Google access token."""
        pass
