from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.sql import func
from flask_login import UserMixin
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from .session import Base


class User(UserMixin, Base):
    """User model for authentication"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(100), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    avatar_url = Column(String(255))
    google_id = Column(String(50), unique=True)
    password_hash = Column(String(255), nullable=True)  # For local authentication
    # Keep the original column name to match existing database
    is_active = Column(Boolean, default=True)  # type: ignore[assignment]
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', name='{self.name}')>"


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
