"""
Domain entities - Pure business logic, no framework dependencies.

Following SOLID principles:
- Single Responsibility: Each entity represents one business concept
- Open/Closed: Entities can be extended without modification
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


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
    role: str = "client"  # 'client', 'artist', 'admin'
    is_active: bool = True
    unified_flow_enabled: bool = False  # Phase 3: Per-user canary flag (defaults OFF)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate domain rules."""
        if not self.name:
            raise ValueError("Name is required")
        # Email is only required for non-artist roles
        if not self.email and self.role != "artist":
            raise ValueError("Email is required")
        # Validate email format only if email is provided
        if self.email and "@" not in self.email:
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

    nome: str = ""
    quantidade: int = 0
    observacoes: Optional[str] = None
    id: Optional[int] = None
    # campos extras removidos para manter compatibilidade
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate business rules."""
        if self.quantidade < 0:
            raise ValueError("Quantidade não pode ser negativa")


@dataclass
class CalendarEvent:
    """
    Domain entity representing a calendar event.
    Pure business logic, no external dependencies.
    """

    id: str = ""
    title: str = ""
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    attendees: Optional[List[str]] = None
    created_by: str = ""
    google_event_id: Optional[str] = None
    user_id: Optional[int] = None
    is_paid: bool = False

    def __post_init__(self):
        """Validate business rules."""
        if self.attendees is None:
            self.attendees = []

        if not self.title.strip():
            raise ValueError("Event title cannot be empty")

        if self.start_time and self.end_time:
            if self.end_time <= self.start_time:
                raise ValueError("End time must be after start time")

    @property
    def duration_minutes(self) -> int:
        """Calculate event duration in minutes."""
        if not self.start_time or not self.end_time:
            return 0
        delta = self.end_time - self.start_time
        return int(delta.total_seconds() / 60)

    @property
    def is_past_event(self) -> bool:
        """Check if event is in the past."""
        if not self.end_time:
            return False
        return self.end_time < datetime.now()


@dataclass
class Client:
    """Domain entity representing a Client."""

    id: Optional[int] = None
    nome: str = ""
    sobrenome: str = ""
    email: str = ""
    telefone: str = ""
    estilo_preferido: str = ""
    parte_corpo: str = ""
    tem_tatuagem: str = ""
    informacoes_extras: str = ""
    jotform_submission_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self):
        """Validate business rules."""
        if not self.nome:
            raise ValueError("Nome is required")
        if self.email and "@" not in self.email:
            raise ValueError("Invalid email format")

    @property
    def full_name(self) -> str:
        """Return full name."""
        return f"{self.nome} {self.sobrenome}".strip()
