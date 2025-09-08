from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    func,
    Date,
    Time,
    Numeric,
    UniqueConstraint,
    JSON,
)
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from flask_login import UserMixin
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from .session import Base
from sqlalchemy.orm import relationship


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


class User(UserMixin, Base):
    """User model for authentication"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(
        String(100), unique=True, nullable=True
    )  # Nullable for artists without email
    name = Column(String(100), nullable=False)
    avatar_url = Column(String(255))
    google_id = Column(String(50), unique=True)
    password_hash = Column(String(255), nullable=True)  # For local authentication
    role = Column(
        String(20), nullable=False, default="client"
    )  # 'client', 'artist', 'admin'
    # Keep the original column name to match existing database
    is_active = Column(Boolean, default=True)  # type: ignore[assignment]
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


# ------------------- ESTOQUE (INVENTORY) -------------------
class Inventory(Base):
    """Inventory model for stock control (Estoque)"""

    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String(100), nullable=True)
    quantidade = Column(Integer, nullable=True)
    observacoes = Column(String(255), nullable=True)
    # Manual order for drag&drop. Nullable: items without manual order appear first (newest first)
    order = Column(Integer, nullable=True, default=None)
    category = Column(String(50), nullable=True)  # Categoria do item
    unit_price = Column(Numeric(10, 2), nullable=True)  # Preço unitário
    supplier = Column(String(100), nullable=True)  # Fornecedor
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Flask-Login required methods - explicit implementation
    def get_id(self):
        """Return user identifier for Flask-Login"""
        return str(self.id)

    @property
    def is_authenticated(self):
        """Return True if user is authenticated"""
        return True

    @property
    def is_anonymous(self):
        """Return True if user is anonymous"""
        return False

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', name='{self.name}')"


class OAuth(OAuthConsumerMixin, Base):
    """OAuth model for storing OAuth tokens"""

    __tablename__ = "oauth"  # type: ignore[assignment]

    provider_user_id = Column(String(256), unique=True, nullable=False)
    user_id = Column(Integer, nullable=False)


class TestModel(Base):
    """Test model to verify database connection"""

    __tablename__ = "test_table"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<TestModel(id={self.id}, name='{self.name}')>"


class Client(Base):
    """Client model for database persistence"""

    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    jotform_submission_id = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<Client(id={self.id}, name='{self.name}', jotform_id='{self.jotform_submission_id}')>"


# SOLID-compliant: Sessao is a top-level entity, not nested, single responsibility
class Sessao(Base):
    """Sessao (Session/Appointment) model for tattoo studio system"""

    __tablename__ = "sessoes"

    id = Column(Integer, primary_key=True, index=True)
    data = Column(Date, nullable=False)
    hora = Column(Time, nullable=False)
    valor = Column(Numeric(10, 2), nullable=False)
    observacoes = Column(String(255))
    cliente_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    artista_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    google_event_id = Column(
        String(100), nullable=True, unique=True
    )  # Added for Google Calendar integration
    status = Column(
        String(20), nullable=False, default="active"
    )  # active, completed, archived
    payment_id = Column(
        Integer, ForeignKey("pagamentos.id"), nullable=True
    )  # Link to payment
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships (ORM navigation)
    cliente = relationship("Client", foreign_keys=[cliente_id], backref="sessoes")
    artista = relationship("User", foreign_keys=[artista_id], backref="sessoes_artista")
    payment = relationship(
        "Pagamento", backref="session", uselist=False, foreign_keys=[payment_id]
    )  # Link to payment

    def __repr__(self):
        return (
            f"<Sessao(id={self.id}, data={self.data}, hora={self.hora}, valor={self.valor}, "
            f"cliente_id={self.cliente_id}, artista_id={self.artista_id}, status={self.status})>"
        )


class Pagamento(Base):
    """Pagamento (Payment) model for financial records"""

    __tablename__ = "pagamentos"

    id = Column(Integer, primary_key=True, index=True)
    data = Column(Date, nullable=False)
    valor = Column(Numeric(10, 2), nullable=False)
    forma_pagamento = Column(String(50), nullable=False)
    observacoes = Column(String(255), nullable=True)
    comissao = Column(Numeric(10, 2), nullable=True)  # For future implementation
    cliente_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    artista_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sessao_id = Column(
        Integer, ForeignKey("sessoes.id"), nullable=True
    )  # Link to session
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    cliente = relationship("Client", foreign_keys=[cliente_id], backref="pagamentos")
    artista = relationship(
        "User", foreign_keys=[artista_id], backref="pagamentos_artista"
    )
    sessao = relationship(
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

    id = Column(Integer, primary_key=True, index=True)
    pagamento_id = Column(Integer, ForeignKey("pagamentos.id"), nullable=True)
    artista_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    percentual = Column(Numeric(5, 2), nullable=False)
    valor = Column(Numeric(10, 2), nullable=False)
    observacoes = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    pagamento = relationship(
        "Pagamento", foreign_keys=[pagamento_id], backref="comissoes"
    )
    artista = relationship("User", foreign_keys=[artista_id])

    def __repr__(self):
        return (
            f"<Comissao(id={self.id}, pagamento_id={self.pagamento_id}, artista_id={self.artista_id}, "
            f"percentual={self.percentual}, valor={self.valor})>"
        )


class Extrato(Base):
    """Snapshot mensal imutável dos dados de pagamentos, sessões e comissões.

    Stored as JSONB so reports are fast to read. Do not reference original
    records by foreign key: data is copied into the JSON payloads.
    """

    __tablename__ = "extratos"
    __table_args__ = (UniqueConstraint("mes", "ano", name="uq_extratos_mes_ano"),)

    id = Column(Integer, primary_key=True, index=True)
    mes = Column(Integer, nullable=False)  # 1..12
    ano = Column(Integer, nullable=False)  # ex.: 2025

    # Snapshots (lists) of objects: pagamentos, sessoes, comissoes
    pagamentos = Column(get_json_type(), nullable=False)
    sessoes = Column(get_json_type(), nullable=False)
    comissoes = Column(get_json_type(), nullable=False)

    # Pre-calculated totals to speed reads and avoid recomputation
    totais = Column(get_json_type(), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Extrato(id={self.id}, mes={self.mes}, ano={self.ano})>"
