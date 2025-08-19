"""
Centralized test configuration following Single Responsibility Principle.

This module provides a single source of truth for all test configuration,
making it easy to modify test behavior without touching multiple files.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


class TestConfig:
    """Centralized test configuration class."""

    # Database configuration
    DATABASE_URL: str = "sqlite:///:memory:"
    TEST_DATABASE_NAME: str = "test_tattoo_studio"

    # Authentication configuration
    JWT_SECRET: str = "test-jwt-secret-key"
    JWT_EXPIRATION_HOURS: int = 1  # Short expiration for tests

    # Flask configuration
    FLASK_ENV: str = "testing"
    FLASK_SECRET_KEY: str = "test-flask-secret"
    TESTING: bool = True
    WTF_CSRF_ENABLED: bool = False  # Disable CSRF for testing

    # Test data configuration
    SAMPLE_USER_EMAIL: str = "test@example.com"
    SAMPLE_USER_NAME: str = "Test User"
    SAMPLE_GOOGLE_ID: str = "test_google_123"

    # Performance configuration
    TEST_TIMEOUT: int = 30  # Max test execution time in seconds
    MAX_TEST_MEMORY_MB: int = 100  # Memory limit for tests

    # Logging configuration
    LOG_LEVEL: str = "ERROR"  # Minimize logging noise in tests
    LOG_FORMAT: str = "%(levelname)s: %(message)s"

    @classmethod
    def get_test_database_url(cls, database_name: str | None = None) -> str:
        """Get test database URL with optional custom name."""
        if database_name:
            return f"sqlite:///:memory:{database_name}:"
        return cls.DATABASE_URL

    @classmethod
    def get_flask_config(cls) -> dict:
        """Get Flask configuration for testing."""
        return {
            "TESTING": cls.TESTING,
            "SECRET_KEY": cls.FLASK_SECRET_KEY,
            "WTF_CSRF_ENABLED": cls.WTF_CSRF_ENABLED,
            "DATABASE_URL": cls.DATABASE_URL,
            "JWT_SECRET_KEY": cls.JWT_SECRET,
        }

    @classmethod
    def setup_test_environment(cls):
        """Setup environment variables for testing."""
        test_env = {
            "FLASK_ENV": cls.FLASK_ENV,
            "DATABASE_URL": cls.DATABASE_URL,
            "JWT_SECRET_KEY": cls.JWT_SECRET,
            "FLASK_SECRET_KEY": cls.FLASK_SECRET_KEY,
        }

        for key, value in test_env.items():
            os.environ[key] = value


# Test data constants
class TestData:
    """Common test data following DRY principle."""

    VALID_USER = {
        "email": "user@example.com",
        "name": "Valid User",
        "google_id": "google_123",
        "avatar_url": "https://example.com/avatar.jpg",
    }

    INVALID_USER_NO_EMAIL = {"name": "No Email User"}

    INVALID_USER_BAD_EMAIL = {"email": "invalid-email", "name": "Bad Email User"}

    VALID_APPOINTMENT = {
        "user_id": 1,
        "service_type": "Tattoo Session",
        "duration_minutes": 120,
        "price": 250.00,
        "notes": "Test appointment",
    }

    GOOGLE_USER_INFO = {
        "id": "google_user_123",
        "email": "google.user@gmail.com",
        "name": "Google User",
        "picture": "https://example.com/google_avatar.jpg",
    }

    JWT_PAYLOAD = {
        "user_id": 123,
        "email": "jwt.user@example.com",
        "exp": None,  # Will be set dynamically
    }


# Test markers for pytest
class TestMarkers:
    """Test markers for organizing test execution."""

    UNIT = "unit"
    INTEGRATION = "integration"
    SLOW = "slow"
    SECURITY = "security"
    DATABASE = "database"
    API = "api"
    DOMAIN = "domain"
    REPOSITORY = "repository"
    SERVICE = "service"
    CONTROLLER = "controller"

    @classmethod
    def get_all_markers(cls) -> list:
        """Get all available test markers."""
        return [
            cls.UNIT,
            cls.INTEGRATION,
            cls.SLOW,
            cls.SECURITY,
            cls.DATABASE,
            cls.API,
            cls.DOMAIN,
            cls.REPOSITORY,
            cls.SERVICE,
            cls.CONTROLLER,
        ]
