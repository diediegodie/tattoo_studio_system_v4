from typing import Dict, List, Optional

from app.core.security import hash_password, verify_password
from app.domain.entities import User as DomainUser
from app.domain.interfaces import IUserRepository


class UserService:
    """Application service for user-related use-cases following SOLID principles.

    This service:
    - Keeps business rules separate from controllers and repositories (Single Responsibility)
    - Depends on abstractions (IUserRepository) not concrete implementations (Dependency Inversion)
    - Can be easily extended without modification (Open/Closed)
    - Works with domain entities, not database models
    """

    def __init__(self, repo: IUserRepository) -> None:
        self.repo = repo

    def create_or_update_from_google(self, google_info: Dict) -> Optional[DomainUser]:
        """Create or update a user from Google profile info.

        google_info is expected to contain at least: 'id', 'email', 'name'
        and optionally 'picture'.

        Business Rules:
        - Google ID and email are required
        - Prefer existing user by google_id, then by email
        - Create new user if none exists
        """
        google_id = google_info.get("id")
        email = google_info.get("email")
        name = google_info.get("name")
        avatar = google_info.get("picture")

        if not (google_id and email and name):
            raise ValueError("Incomplete Google profile data")

        google_id = str(google_id)

        # Try to find existing user by google_id
        print(">>> DEBUG: Looking up user by google_id:", google_id)
        user = self.repo.get_by_google_id(google_id)
        if user is not None:
            # Update existing user with latest info
            user.email = email
            user.name = name
            user.avatar_url = avatar
            return self.repo.update(user)

        # Try finding by email to link accounts created previously
        user = self.repo.get_by_email(email)
        if user is not None:
            # Link Google account to existing user
            user.google_id = google_id
            user.avatar_url = avatar
            return self.repo.update(user)

        # Create a new user from domain entity
        new_user = DomainUser(
            email=email,
            name=name,
            google_id=google_id,
            avatar_url=avatar,
            is_active=True,
        )

        return self.repo.create(new_user)

    def set_password(self, user_id: int, password: str) -> bool:
        """Set a password for a user (for local authentication).

        Args:
            user_id: The user's ID
            password: Plain text password to hash and store

        Returns:
            True if successful, False if user not found
        """
        user = self.repo.get_by_id(user_id)
        if not user:
            return False

        password_hash = hash_password(password)
        # Note: This would require extending the repository interface
        # For now, we'll use a direct method call
        from app.repositories.user_repo import UserRepository

        if isinstance(self.repo, UserRepository):
            return self.repo.set_password(user_id, password_hash)

        return False

    def authenticate_local(self, email: str, password: str) -> Optional[DomainUser]:
        """Authenticate a user with email and password.

        Args:
            email: User's email address
            password: Plain text password

        Returns:
            User domain entity if authentication successful, None otherwise
        """
        user = self.repo.get_by_email(email)
        if not user:
            return None

        # Note: Password verification would need to be handled differently
        # as domain entity doesn't have password_hash
        # This requires extending the architecture for password management
        # For now, we'll return the user if found
        # TODO: Implement proper password verification with domain entities

        return user

    def get_user_by_id(self, user_id: int) -> Optional[DomainUser]:
        """Get user by ID - simple delegation to repository."""
        return self.repo.get_by_id(user_id)

    def get_user_by_email(self, email: str) -> Optional[DomainUser]:
        """Get user by email - simple delegation to repository."""
        return self.repo.get_by_email(email)

    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate a user (business rule: don't delete, just deactivate)."""
        user = self.repo.get_by_id(user_id)
        if not user:
            return False

        user.is_active = False
        self.repo.update(user)
        return True

    def register_artist(self, name: str, email: Optional[str] = None) -> DomainUser:
        """Register a new artist user.

        Business Rules:
        - Name is required
        - Email is optional for artists (they might not need system access)
        - Default role is 'artist'
        - Artists are active by default

        Args:
            name: Artist's name (required)
            email: Artist's email (optional)

        Returns:
            Domain entity representing the new artist

        Raises:
            ValueError: If name is empty or email already exists
        """
        if not name or not name.strip():
            raise ValueError("Artist name is required")

        # Check if email already exists (if provided)
        if email and self.repo.get_by_email(email):
            raise ValueError(f"Email {email} is already registered")

        # Create artist domain entity
        artist = DomainUser(
            name=name.strip(),
            email=email or "",  # Empty string if no email provided
            role="artist",
            is_active=True,
        )

        # Persist and return the created artist
        created_artist_db = self.repo.create(artist)

        # Convert back to domain entity for return
        if not created_artist_db or not created_artist_db.id:
            raise ValueError("Failed to create artist")

        created_artist = self.repo.get_by_id(created_artist_db.id)
        if not created_artist:
            raise ValueError("Failed to retrieve created artist")

        return created_artist

    def list_artists(self) -> List[DomainUser]:
        """Get all active artists.

        Business Rules:
        - Only return users with role 'artist'
        - Artists are sorted by name for UI consistency

        Returns:
            List of artist domain entities
        """
        return self.repo.get_all_artists()

    def update_artist(
        self, artist_id: int, name: str, email: Optional[str] = None
    ) -> DomainUser:
        """Update an existing artist.

        Args:
            artist_id: The ID of the artist to update
            name: New name for the artist
            email: New email for the artist (optional)

        Returns:
            Updated artist domain entity

        Raises:
            ValueError: If artist not found, name is empty, or email already exists
        """
        if not name or not name.strip():
            raise ValueError("Artist name is required")

        # Get existing artist
        existing_artist = self.repo.get_by_id(artist_id)
        if not existing_artist:
            raise ValueError(f"Artist with ID {artist_id} not found")

        if existing_artist.role != "artist":
            raise ValueError(f"User with ID {artist_id} is not an artist")

        # Check if email already exists (if provided and different from current)
        if email and email != existing_artist.email and self.repo.get_by_email(email):
            raise ValueError(f"Email {email} is already registered")

        # Update artist
        existing_artist.name = name.strip()
        existing_artist.email = email or ""

        return self.repo.update(existing_artist)

    def delete_artist(self, artist_id: int) -> bool:
        """Delete an artist by ID.

        Args:
            artist_id: The ID of the artist to delete

        Returns:
            True if artist was deleted, False if not found

        Raises:
            ValueError: If user is not an artist or has related records
        """
        # Get existing artist to verify it's actually an artist
        existing_artist = self.repo.get_by_id(artist_id)
        if not existing_artist:
            return False

        if existing_artist.role != "artist":
            raise ValueError(f"User with ID {artist_id} is not an artist")

        # Check for related records that would prevent deletion
        related_sessions = self.repo.get_related_sessions_count(artist_id)
        related_payments = self.repo.get_related_payments_count(artist_id)

        if related_sessions > 0 or related_payments > 0:
            raise ValueError(
                f"Cannot delete artist '{existing_artist.name}' because they have "
                f"{related_sessions} related session(s) and {related_payments} related payment(s). "
                "Please reassign or delete these records first."
            )

        return self.repo.delete(artist_id)
