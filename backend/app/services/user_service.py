from typing import Dict, Optional

from domain.interfaces import IUserRepository
from domain.entities import User as DomainUser
from core.security import hash_password, verify_password


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
        google_id = str(google_info.get("id"))
        email = google_info.get("email")
        name = google_info.get("name")
        avatar = google_info.get("picture")

        if not (google_id and email and name):
            raise ValueError("Incomplete Google profile data")

        # Try to find existing user by google_id
        user = self.repo.get_by_google_id(google_id)
        if user is not None:
            # Update existing user with latest info
            user.email = email
            user.name = name
            user.avatar_url = avatar
            self.repo.update(user)
            # Retorna modelo de persistência para autenticação
            from repositories.user_repo import UserRepository

            if isinstance(self.repo, UserRepository):
                return self.repo.get_db_by_google_id(google_id)
            else:
                return user

        # Try finding by email to link accounts created previously
        user = self.repo.get_by_email(email)
        if user is not None:
            # Link Google account to existing user
            user.google_id = google_id
            user.avatar_url = avatar
            self.repo.update(user)
            # Retorna modelo de persistência para autenticação
            from repositories.user_repo import UserRepository

            if isinstance(self.repo, UserRepository):
                return self.repo.get_db_by_google_id(google_id)
            else:
                return user

        # Create a new user from domain entity
        new_user = DomainUser(
            email=email,
            name=name,
            google_id=google_id,
            avatar_url=avatar,
            is_active=True,
        )

        self.repo.create(new_user)
        # Para autenticação, retorna o modelo de persistência
        # Cast necessário para acessar método específico do repositório concreto
        from repositories.user_repo import UserRepository

        if isinstance(self.repo, UserRepository):
            return self.repo.get_db_by_google_id(google_id)
        else:
            # Fallback caso não seja o repositório concreto
            return self.repo.get_by_google_id(google_id)

    def set_password(self, user_id: int, [REDACTED_PASSWORD] -> bool:
        """Set a password for a user (for local authentication).

        Args:
            user_id: The user's ID
            [REDACTED_PASSWORD] text password to hash and store

        Returns:
            True if successful, False if user not found
        """
        user = self.repo.get_by_id(user_id)
        if not user:
            return False

        password_hash = hash_password(password)
        # Note: This would require extending the repository interface
        # For now, we'll use a direct method call
        from repositories.user_repo import UserRepository

        if isinstance(self.repo, UserRepository):
            return self.repo.set_password(user_id, password_hash)

        return False

    def authenticate_local(self, email: str, [REDACTED_PASSWORD] -> Optional[DomainUser]:
        """Authenticate a user with email and password.

        Args:
            email: User's email address
            [REDACTED_PASSWORD] text password

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
