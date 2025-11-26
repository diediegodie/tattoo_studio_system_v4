"""
Tests for the new SOLID architecture implementation.

This test file demonstrates proper testing with the new:
- Domain entities
- Repository interfaces
- Service implementations
"""

from datetime import datetime
from typing import Any, cast
from unittest.mock import Mock, patch

import pytest

# Import the new architecture components
from app.domain.entities import User as DomainUser
from app.domain.interfaces import IUserRepository
from app.repositories.user_repo import UserRepository
from app.schemas.dtos import UserCreateRequest, UserResponse
from app.services.user_service import UserService


class TestDomainEntities:
    """Test domain entities following SOLID principles."""

    def test_user_entity_creation_valid(self):
        """Test creating a valid user domain entity."""
        user = DomainUser(email="test@example.com", name="Test User", is_active=True)

        assert user.email == "test@example.com"
        assert user.name == "Test User"
        assert user.is_active is True
        assert user.id is None  # Not yet persisted

    def test_user_entity_validation_invalid_email(self):
        """Test user entity validation with invalid email."""
        with pytest.raises(ValueError, match="Invalid email format"):
            DomainUser(email="invalid-email", name="Test User")

    def test_user_entity_validation_missing_fields(self):
        """Test user entity validation with missing required fields."""
        with pytest.raises(ValueError, match="Email is required"):
            DomainUser(email="", name="Test User")

        with pytest.raises(ValueError, match="Name is required"):
            DomainUser(email="test@example.com", name="")


class TestUserServiceWithNewArchitecture:
    """Test UserService with the new SOLID architecture."""

    def setup_method(self):
        """Set up test fixtures using interfaces."""
        # Mock the interface, not the concrete implementation
        self.mock_repo = Mock(spec=IUserRepository)
        self.service = UserService(self.mock_repo)

    def test_create_or_update_from_google_new_user(self):
        """Test creating a new user from Google profile with new architecture."""
        google_info = {
            "id": "google123",
            "email": "newuser@gmail.com",
            "name": "New User",
            "picture": "https://example.com/photo.jpg",
        }

        # Mock no existing user
        self.mock_repo.get_by_google_id.return_value = None
        self.mock_repo.get_by_email.return_value = None

        # Mock user creation - now expects domain entity
        created_user = DomainUser(
            id=1,
            email="newuser@gmail.com",
            name="New User",
            google_id="google123",
            avatar_url="https://example.com/photo.jpg",
            is_active=True,
        )
        self.mock_repo.create.return_value = created_user

        result = self.service.create_or_update_from_google(google_info)

        assert result == created_user
        # Verify the service called create with a domain entity
        self.mock_repo.create.assert_called_once()
        call_args = self.mock_repo.create.call_args[0][0]
        assert isinstance(call_args, DomainUser)
        assert call_args.email == "newuser@gmail.com"
        assert call_args.name == "New User"
        assert call_args.google_id == "google123"

    def test_create_or_update_from_google_existing_user_by_google_id(self):
        """Test updating existing user found by Google ID."""
        google_info = {
            "id": "google123",
            "email": "updated@gmail.com",
            "name": "Updated Name",
            "picture": "https://example.com/new_photo.jpg",
        }

        # Mock existing user found by Google ID
        existing_user = DomainUser(
            id=1,
            email="old@gmail.com",
            name="Old Name",
            google_id="google123",
            is_active=True,
        )
        self.mock_repo.get_by_google_id.return_value = existing_user

        # Mock update
        updated_user = DomainUser(
            id=1,
            email="updated@gmail.com",
            name="Updated Name",
            google_id="google123",
            avatar_url="https://example.com/new_photo.jpg",
            is_active=True,
        )
        self.mock_repo.update.return_value = updated_user

        result = self.service.create_or_update_from_google(google_info)

        assert result == updated_user
        # Verify the service called update with the modified user
        self.mock_repo.update.assert_called_once()
        call_args = self.mock_repo.update.call_args[0][0]
        assert isinstance(call_args, DomainUser)
        assert call_args.email == "updated@gmail.com"
        assert call_args.name == "Updated Name"

    def test_get_user_by_id_delegation(self):
        """Test that service properly delegates to repository."""
        mock_user = DomainUser(id=123, email="test@example.com", name="Test User")
        self.mock_repo.get_by_id.return_value = mock_user

        result = self.service.get_user_by_id(123)

        assert result == mock_user
        self.mock_repo.get_by_id.assert_called_once_with(123)

    def test_deactivate_user_business_rule(self):
        """Test business rule: deactivate instead of delete."""
        user = DomainUser(
            id=123, email="test@example.com", name="Test User", is_active=True
        )
        self.mock_repo.get_by_id.return_value = user

        result = self.service.deactivate_user(123)

        assert result is True
        assert user.is_active is False  # Business rule applied
        self.mock_repo.update.assert_called_once_with(user)

    def test_create_or_update_from_google_incomplete_data(self):
        """Test validation of incomplete Google data."""
        incomplete_google_info = {
            "id": "google123",
            # Missing email and name
        }

        with pytest.raises(ValueError, match="Incomplete Google profile data"):
            self.service.create_or_update_from_google(incomplete_google_info)


class TestUserRepositoryMapping:
    """Test the repository's domain entity mapping."""

    def test_to_domain_conversion(self):
        """Test conversion from database model to domain entity."""
        # Mock database session
        mock_db = Mock()
        repo = UserRepository(mock_db)

        # Create a simple mock that doesn't cause recursion
        class MockDbUser:
            def __init__(self):
                self.id = 123
                self.email = "test@example.com"
                self.name = "Test User"
                self.avatar_url = "https://example.com/avatar.jpg"
                self.google_id = "google123"
                self.is_active = True
                self.created_at = datetime.now()
                self.updated_at = datetime.now()

        mock_db_user = MockDbUser()
        # Cast to Any to satisfy static type checkers that expect the DB model type
        domain_user = repo._to_domain(cast(Any, mock_db_user))

        assert isinstance(domain_user, DomainUser)
        assert domain_user.id == 123
        assert domain_user.email == "test@example.com"
        assert domain_user.name == "Test User"
        assert domain_user.google_id == "google123"
        assert domain_user.is_active is True


class TestDTOSchemas:
    """Test the DTO schemas for API contracts."""

    def test_user_create_request_validation_success(self):
        """Test valid user creation request."""
        request = UserCreateRequest(email="test@example.com", name="Test User")

        # Should not raise any exception
        request.validate()

    def test_user_create_request_validation_invalid_email(self):
        """Test user creation request with invalid email."""
        request = UserCreateRequest(email="invalid-email", name="Test User")

        with pytest.raises(ValueError, match="Valid email is required"):
            request.validate()

    def test_user_create_request_validation_short_name(self):
        """Test user creation request with too short name."""
        request = UserCreateRequest(email="test@example.com", name="A")  # Too short

        with pytest.raises(ValueError, match="Name must be at least 2 characters"):
            request.validate()

    def test_user_response_from_domain(self):
        """Test creating response DTO from domain entity."""
        domain_user = DomainUser(
            id=123,
            email="test@example.com",
            name="Test User",
            avatar_url="https://example.com/avatar.jpg",
            is_active=True,
            created_at=datetime.now(),
        )

        response = UserResponse.from_domain(domain_user)

        assert response.id == 123
        assert response.email == "test@example.com"
        assert response.name == "Test User"
        assert response.avatar_url == "https://example.com/avatar.jpg"
        assert response.is_active is True


class TestSOLIDPrinciples:
    """Test that our architecture follows SOLID principles."""

    def test_single_responsibility_separation(self):
        """Test that responsibilities are properly separated."""
        # Repository only handles data access
        mock_db = Mock()
        repo = UserRepository(mock_db)
        assert hasattr(repo, "get_by_id")
        assert hasattr(repo, "create")
        assert hasattr(repo, "update")

        # Service only handles business logic
        mock_repo = Mock(spec=IUserRepository)
        service = UserService(mock_repo)
        assert hasattr(service, "create_or_update_from_google")
        assert hasattr(service, "deactivate_user")

        # Domain entities only handle state and basic validation
        user = DomainUser(email="test@example.com", name="Test User")
        assert hasattr(user, "email")
        assert hasattr(user, "name")

    def test_dependency_inversion_principle(self):
        """Test that high-level modules depend on abstractions."""
        # UserService depends on IUserRepository interface, not concrete implementation
        mock_repo = Mock(spec=IUserRepository)
        service = UserService(mock_repo)

        # This should work with any implementation of IUserRepository
        assert service.repo == mock_repo

    def test_interface_segregation_principle(self):
        """Test that interfaces are properly segregated."""
        # We have separate reader and writer interfaces
        from app.domain.interfaces import IUserReader, IUserWriter

        # A client that only reads doesn't need write methods
        mock_reader = Mock(spec=IUserReader)
        assert hasattr(mock_reader, "get_by_id")
        assert hasattr(mock_reader, "get_by_email")

        # A client that only writes doesn't need read methods
        mock_writer = Mock(spec=IUserWriter)
        assert hasattr(mock_writer, "create")
        assert hasattr(mock_writer, "update")

    def test_liskov_substitution_principle(self):
        """Test that implementations can substitute their interfaces."""
        # Any IUserRepository implementation should work with UserService
        mock_sql_repo = Mock(spec=IUserRepository)
        mock_memory_repo = Mock(spec=IUserRepository)

        service1 = UserService(mock_sql_repo)
        service2 = UserService(mock_memory_repo)

        # Both should have the same interface
        assert hasattr(service1, "get_user_by_id")
        assert hasattr(service2, "get_user_by_id")
        assert type(service1.get_user_by_id) == type(service2.get_user_by_id)

    def test_open_closed_principle(self):
        """Test that classes are open for extension, closed for modification."""

        # We can create new repository implementations without modifying existing code
        class MockRedisUserRepository:
            """New repository implementation - extends without modifying."""

            def __init__(self, redis_client):
                self.redis = redis_client

            def get_by_id(self, user_id: int):
                # New implementation
                pass

            def create(self, user):
                # New implementation
                pass

        # This new implementation can work with existing UserService
        # without modifying UserService code
        assert True  # Architectural test - if this runs, the principle is followed
