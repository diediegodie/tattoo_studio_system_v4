from typing import List, Optional

from app.db.base import User as DbUser
from app.domain.entities import User as DomainUser
from app.domain.interfaces import IUserRepository
from sqlalchemy.orm.attributes import InstrumentedAttribute


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
        # Debug which engine/dialect this repository is using
        try:
            bind = getattr(self.db, "bind", None) or self.db.get_bind()
        except Exception:
            bind = None
        if bind is not None:
            try:
                print(
                    ">>> DEBUG: user_repo engine URL:", getattr(bind, "url", "unknown")
                )
                print(
                    ">>> DEBUG: user_repo dialect:",
                    getattr(getattr(bind, "dialect", None), "name", "unknown"),
                )
            except Exception as _e:
                print(">>> DEBUG: user_repo engine inspection failed:", str(_e))
        else:
            print(">>> DEBUG: user_repo session has no bind yet")

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

    def get_all_artists(self) -> List[DomainUser]:
        """Get all users with role 'artist', returning domain entities."""
        db_artists = (
            self.db.query(DbUser).filter_by(role="artist").order_by(DbUser.name).all()
        )
        return [self._to_domain(db_artist) for db_artist in db_artists]

    def create(self, user: DomainUser) -> DbUser:
        """Create a new user from domain entity and return persistence model."""
        db_user = DbUser()
        # Handle empty email for unique constraint - use None instead of empty string
        db_user.email = user.email if user.email else None  # type: ignore
        db_user.name = user.name  # type: ignore
        db_user.google_id = user.google_id  # type: ignore
        db_user.avatar_url = user.avatar_url  # type: ignore
        db_user.role = user.role  # type: ignore
        _assign_if_model_attribute(db_user, "is_active", user.is_active)

        self.db.add(db_user)
        self.db.commit()
        self.db.refresh(db_user)

        # Return the persistence model
        return db_user

    def update(self, user: DomainUser) -> DomainUser:
        """Update an existing user from domain entity."""
        if not user.id:
            raise ValueError("User ID is required for update")

        db_user = self.db.query(DbUser).filter_by(id=user.id).first()
        if not db_user:
            raise ValueError(f"User with ID {user.id} not found")

        # Update fields from domain entity
        # Handle empty email for unique constraint - use None instead of empty string
        db_user.email = user.email if user.email else None  # type: ignore
        db_user.name = user.name  # type: ignore
        db_user.google_id = user.google_id  # type: ignore
        db_user.avatar_url = user.avatar_url  # type: ignore
        db_user.role = user.role  # type: ignore
        _assign_if_model_attribute(db_user, "is_active", user.is_active)

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

    def get_related_sessions_count(self, user_id: int) -> int:
        """Get count of sessions related to a user."""
        from app.db.base import Sessao

        return self.db.query(Sessao).filter_by(artista_id=user_id).count()

    def get_related_payments_count(self, user_id: int) -> int:
        """Get count of payments related to a user."""
        from app.db.base import Pagamento

        return self.db.query(Pagamento).filter_by(artista_id=user_id).count()

    def _to_domain(self, db_user: DbUser) -> DomainUser:
        """Convert database model to domain entity."""
        return DomainUser(
            id=getattr(db_user, "id"),
            email=getattr(db_user, "email", None)
            or "",  # Convert NULL to empty string for domain
            name=getattr(db_user, "name"),
            avatar_url=getattr(db_user, "avatar_url", None),
            google_id=getattr(db_user, "google_id", None),
            role=getattr(db_user, "role", "client"),
            is_active=getattr(db_user, "is_active", True),
            unified_flow_enabled=getattr(
                db_user, "unified_flow_enabled", False
            ),  # Phase 3: Per-user flag
            created_at=getattr(db_user, "created_at", None),
            updated_at=getattr(db_user, "updated_at", None),
        )


def _assign_if_model_attribute(model: DbUser, name: str, value):
    """Assign value to SQLAlchemy attribute only if underlying column exists."""
    descriptor = getattr(model.__class__, name, None)
    if isinstance(descriptor, InstrumentedAttribute):
        setattr(model, name, value)
