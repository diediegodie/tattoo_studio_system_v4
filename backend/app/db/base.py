from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .session import Base


def get_json_type():
    """Return appropriate JSON type based on database dialect."""
    # For PostgreSQL, use JSONB for better performance
    # For SQLite and other databases, use JSON
    try:
        from flask import current_app

        if current_app and "postgresql" in current_app.config.get(
            "SQLALCHEMY_DATABASE_URI", ""
        ):
            return JSONB
        else:
            return JSON
    except (RuntimeError, ImportError):
        # Fallback to JSON if Flask context is not available
        return JSON


# Explicitly implement Flask-Login interface without inheriting UserMixin
class User(Base):
    """User model for authentication"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(
        String(100), unique=True, nullable=True
    )  # Nullable for artists without email
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    google_id: Mapped[Optional[str]] = mapped_column(String(50), unique=True)
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )  # For local authentication
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="client"
    )  # 'client', 'artist', 'admin'
    # Explicit active flag to support Flask-Login semantics and tests
    active_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    @property
    def is_active(self) -> bool:
        # Flask-Login expects this property
        return self.active_flag

    @is_active.setter
    def is_active(self, value: bool) -> None:
        """Allow tests and callers to set is_active while persisting to active_flag.

        This maintains backward-compatible semantics with Flask-Login and
        enables SQLAlchemy model construction with is_active=... as used in tests.
        """
        self.active_flag = bool(value)

    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    # Flask-Login required methods/properties - ensure explicit behavior
    def get_id(self):
        """Return user identifier for Flask-Login"""
        return str(self.id)

    @property
    def is_authenticated(self):
        """Return True if user is authenticated (identity exists)."""
        return True

    @property
    def is_anonymous(self):
        """Return True if user is anonymous (never for persisted users)."""
        return False


# ------------------- ESTOQUE (INVENTORY) -------------------
class Inventory(Base):
    """Inventory model for stock control (Estoque)"""

    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nome: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    quantidade: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    observacoes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Manual order for drag&drop. Nullable: items without manual order appear first (newest first)
    order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    unit_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    supplier: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    def __repr__(self):
        return f"<Inventory(id={self.id}, nome='{self.nome}', quantidade={self.quantidade})>"


class OAuth(OAuthConsumerMixin, Base):
    """OAuth model for storing OAuth tokens"""

    __tablename__ = "oauth"  # type: ignore[assignment]

    provider_user_id: Mapped[str] = mapped_column(
        String(256), unique=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # Override the token field from OAuthConsumerMixin to use JSONB for PostgreSQL
    # Use SQLAlchemy 2.0 typed ORM annotations so static type checkers know
    # the instance attribute is a dict, not a Column. MutableDict enables
    # change tracking for in-place JSON mutations.
    token: Mapped[dict[str, Any]] = mapped_column(
        # Use JSONB on Postgres, JSON on SQLite/others for test compatibility
        MutableDict.as_mutable(get_json_type()()),
        nullable=False,
    )


class TestModel(Base):
    """Test model to verify database connection"""

    __tablename__ = "test_table"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    def __repr__(self):
        return f"<TestModel(id={self.id}, name='{self.name}')>"


class Client(Base):
    """Client model for database persistence"""

    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    jotform_submission_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    def __repr__(self):
        return f"<Client(id={self.id}, name='{self.name}', jotform_id='{self.jotform_submission_id}')>"


# SOLID-compliant: Sessao is a top-level entity, not nested, single responsibility
class Sessao(Base):
    """Sessao (Session/Appointment) model for tattoo studio system"""

    __tablename__ = "sessoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    data: Mapped[date] = mapped_column(Date, nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    observacoes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    cliente_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("clients.id"), nullable=False, index=True
    )
    artista_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    google_event_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, unique=True
    )  # Added for Google Calendar integration
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active"
    )  # active, completed, archived
    payment_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("pagamentos.id"), nullable=True, index=True
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    # Relationships (ORM navigation)
    cliente: Mapped["Client"] = relationship(
        "Client", foreign_keys=[cliente_id], backref="sessoes"
    )
    artista: Mapped["User"] = relationship(
        "User", foreign_keys=[artista_id], backref="sessoes_artista"
    )
    payment: Mapped[Optional["Pagamento"]] = relationship(
        "Pagamento", backref="session", uselist=False, foreign_keys=[payment_id]
    )  # Link to payment

    def __repr__(self):
        return (
            f"<Sessao(id={self.id}, data={self.data}, valor={self.valor}, "
            f"cliente_id={self.cliente_id}, artista_id={self.artista_id}, status={self.status})>"
        )


class Pagamento(Base):
    """Pagamento (Payment) model for financial records"""

    __tablename__ = "pagamentos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    data: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    forma_pagamento: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    observacoes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    comissao: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    cliente_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("clients.id"), nullable=True, index=True
    )
    artista_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    sessao_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("sessoes.id"), nullable=True, index=True
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    # Relationships
    cliente: Mapped[Optional["Client"]] = relationship(
        "Client", foreign_keys=[cliente_id], backref="pagamentos"
    )
    artista: Mapped["User"] = relationship(
        "User", foreign_keys=[artista_id], backref="pagamentos_artista"
    )
    sessao: Mapped[Optional["Sessao"]] = relationship(
        "Sessao", backref="pagamento", uselist=False, foreign_keys=[sessao_id]
    )  # Link to session

    def __repr__(self):
        return (
            f"<Pagamento(id={self.id}, data={self.data}, valor={self.valor}, "
            f"forma_pagamento={self.forma_pagamento}, sessao_id={self.sessao_id})>"
        )


class Comissao(Base):
    """Comissao model to record commissions for artists based on pagamentos."""

    __tablename__ = "comissoes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    pagamento_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("pagamentos.id"), nullable=True, index=True
    )
    artista_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    percentual: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    observacoes: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    pagamento: Mapped[Optional["Pagamento"]] = relationship(
        "Pagamento", foreign_keys=[pagamento_id], backref="comissoes"
    )
    artista: Mapped["User"] = relationship("User", foreign_keys=[artista_id])

    def __repr__(self):
        return (
            f"<Comissao(id={self.id}, pagamento_id={self.pagamento_id}, artista_id={self.artista_id}, "
            f"percentual={self.percentual}, valor={self.valor})>"
        )


class Gasto(Base):
    """Gasto (Expense) model to track studio outgoing funds.

    Mirrors patterns from Pagamento (valor, data, forma_pagamento) and links
    to the creating user via `created_by`.
    """

    __tablename__ = "gastos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    data: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    valor: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    descricao: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    forma_pagamento: Mapped[str] = mapped_column(String(50), nullable=False)
    created_by: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    # Relationships
    creator: Mapped["User"] = relationship(
        "User", foreign_keys=[created_by], backref="gastos_criados"
    )

    def __repr__(self):
        return (
            f"<Gasto(id={self.id}, data={self.data}, valor={self.valor}, "
            f"forma_pagamento={self.forma_pagamento}, created_by={self.created_by})>"
        )


class Extrato(Base):
    """Immutable monthly snapshot of payment, session, and commission data.

    Stored as JSONB so reports are fast to read. Do not reference original
    records by foreign key: data is copied into the JSON payloads.
    """

    __tablename__ = "extratos"
    __table_args__ = (UniqueConstraint("mes", "ano", name="uq_extratos_mes_ano"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mes: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # 1..12
    ano: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # ex.: 2025

    # Snapshots (lists) of objects: pagamentos, sessoes, comissoes, gastos
    pagamentos: Mapped[Any] = mapped_column(get_json_type(), nullable=False)
    sessoes: Mapped[Any] = mapped_column(get_json_type(), nullable=False)
    comissoes: Mapped[Any] = mapped_column(get_json_type(), nullable=False)
    gastos: Mapped[Optional[Any]] = mapped_column(get_json_type(), nullable=True)

    # Pre-calculated totals to speed reads and avoid recomputation
    totais: Mapped[Any] = mapped_column(get_json_type(), nullable=False)

    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self):
        return f"<Extrato(id={self.id}, mes={self.mes}, ano={self.ano})>"


class ExtratoRunLog(Base):
    """Log table to track when extrato generation runs to prevent duplicates."""

    __tablename__ = "extrato_run_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    mes: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    ano: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    __table_args__ = (
        UniqueConstraint("mes", "ano", "status", name="unique_extrato_run_per_month"),
    )

    def __repr__(self):
        return f"<ExtratoRunLog(id={self.id}, mes={self.mes}, ano={self.ano}, status={self.status})>"


class ExtratoSnapshot(Base):
    """Snapshot of extrato data for undo operations."""

    __tablename__ = "extrato_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    snapshot_id: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    mes: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    ano: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    data: Mapped[Any] = mapped_column(
        get_json_type(), nullable=False
    )  # JSON snapshot of extrato data
    correlation_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    def __repr__(self):
        return f"<ExtratoSnapshot(id={self.id}, snapshot_id={self.snapshot_id}, mes={self.mes}, ano={self.ano})>"
