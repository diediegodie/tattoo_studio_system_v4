from typing import Optional

from domain.interfaces import IUserRepository
from domain.entities import User as DomainUser
from db.base import User as DbUser


class UserRepository(IUserRepository):
    def get_db_by_google_id(self, google_id: str) -> Optional[DbUser]:
        """Get user by Google ID, returning database model."""
        return self.db.query(DbUser).filter_by(google_id=google_id).first()

    def get_db_by_email(self, email: str) -> Optional[DbUser]:
        """Get user by email, returning database model."""
        return self.db.query(DbUser).filter_by(email=email).first()

    """Repository for User persistence operations following SOLID principles.

    This implementation:
    - Implements IUserRepository interface (Dependency Inversion)
    - Handles data access only (Single Responsibility)
    - Can be easily substituted (Liskov Substitution)
    - Maps between domain entities and database models
    """

    def __init__(self, db_session) -> None:
        self.db = db_session

    def get_by_id(self, user_id: int) -> Optional[DomainUser]:
        """Get user by ID, returning domain entity."""
        db_user = self.db.query(DbUser).filter_by(id=user_id).first()
        return self._to_domain(db_user) if db_user else None

    def get_by_email(self, email: str) -> Optional[DomainUser]:
        """Get user by email, returning domain entity."""
        db_user = self.db.query(DbUser).filter_by(email=email).first()
        return self._to_domain(db_user) if db_user else None

    def get_by_google_id(self, google_id: str) -> Optional[DomainUser]:
        """Get user by Google ID, returning domain entity."""
        db_user = self.db.query(DbUser).filter_by(google_id=google_id).first()
        return self._to_domain(db_user) if db_user else None

    def create(self, user: DomainUser) -> DbUser:
        """Create a new user from domain entity and return persistence model."""
        db_user = DbUser()
        db_user.email = user.email  # type: ignore
        db_user.name = user.name  # type: ignore
        db_user.google_id = user.google_id  # type: ignore
        db_user.avatar_url = user.avatar_url  # type: ignore
        db_user.is_active = user.is_active  # type: ignore

        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)

        # Retorna o modelo de persistência usando o google_id
        return self.get_db_by_google_id(str(db_user.google_id))

    def update(self, user: DomainUser) -> DomainUser:
        """Update an existing user from domain entity."""
        if not user.id:
            raise ValueError("User ID is required for update")

        db_user = self.db.query(DbUser).filter_by(id=user.id).first()
        if not db_user:
            raise ValueError(f"User with ID {user.id} not found")

        # Update fields from domain entity
        db_user.email = user.email  # type: ignore
        db_user.name = user.name  # type: ignore
        db_user.google_id = user.google_id  # type: ignore
        db_user.avatar_url = user.avatar_url  # type: ignore
        db_user.is_active = user.is_active  # type: ignore

        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)

        return self._to_domain(db_user)

    def delete(self, user_id: int) -> bool:
        """Delete a user by ID."""
        db_user = self.db.query(DbUser).filter_by(id=user_id).first()
        if not db_user:
            return False

        self.db.delete(db_user)
        self.db.commit()
        return True

    def set_password(self, user_id: int, password_hash: str) -> bool:
        """Set the password hash for a user."""
        db_user = self.db.query(DbUser).filter_by(id=user_id).first()
        if not db_user:
            return False

        db_user.password_hash = password_hash  # type: ignore
        self.db.add(db_user)
        self.db.commit()
        return True

    def _to_domain(self, db_user: DbUser) -> DomainUser:
        """Convert database model to domain entity."""
        return DomainUser(
            id=getattr(db_user, "id"),
            email=getattr(db_user, "email"),
            name=getattr(db_user, "name"),
            avatar_url=getattr(db_user, "avatar_url", None),
            google_id=getattr(db_user, "google_id", None),
            is_active=getattr(db_user, "is_active", True),
            created_at=getattr(db_user, "created_at", None),
            updated_at=getattr(db_user, "updated_at", None),
        )
