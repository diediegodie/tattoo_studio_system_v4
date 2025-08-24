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
)
from sqlalchemy.sql import func
from flask_login import UserMixin
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from .session import Base
from sqlalchemy.orm import relationship


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
    order = Column(Integer, nullable=False, default=0)  # Ordem para drag&drop
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
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships (ORM navigation)
    cliente = relationship("Client", foreign_keys=[cliente_id], backref="sessoes")
    artista = relationship("User", foreign_keys=[artista_id], backref="sessoes_artista")

    def __repr__(self):
        return (
            f"<Sessao(id={self.id}, data={self.data}, hora={self.hora}, valor={self.valor}, "
            f"cliente_id={self.cliente_id}, artista_id={self.artista_id})>"
        )
