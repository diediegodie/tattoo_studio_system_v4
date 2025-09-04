"""
Client repository implementation following SOLID principles.

This implementation:
- Implements IClientRepository interface (Dependency Inversion)
- Handles data access only (Single Responsibility)
- Can be easily substituted (Liskov Substitution)
- Maps between domain entities and database models
"""

from typing import Optional, List
from app.domain.interfaces import IClientRepository
from app.domain.entities import Client as DomainClient
from app.db.base import Client as DbClient


class ClientRepository(IClientRepository):
    """Repository for Client persistence operations following SOLID principles."""

    def __init__(self, db_session) -> None:
        self.db = db_session

    def get_by_id(self, client_id: int) -> Optional[DomainClient]:
        """Get client by ID, returning domain entity."""
        db_client = self.db.query(DbClient).filter_by(id=client_id).first()
        return self._to_domain(db_client) if db_client else None

    def get_all(self) -> List[DomainClient]:
        """Get all clients, returning domain entities."""
        db_clients = self.db.query(DbClient).all()
        return [self._to_domain(client) for client in db_clients]

    def get_by_jotform_id(self, jotform_id: str) -> Optional[DomainClient]:
        """Get client by JotForm submission ID, returning domain entity."""
        db_client = (
            self.db.query(DbClient).filter_by(jotform_submission_id=jotform_id).first()
        )
        return self._to_domain(db_client) if db_client else None

    def create(self, client: DomainClient) -> DomainClient:
        """Create a new client from domain entity."""
        # Use constructor pattern to avoid type assignment issues
        db_client = DbClient(
            name=str(client.full_name),
            jotform_submission_id=str(client.jotform_submission_id),
        )

        self.db.add(db_client)
        self.db.commit()
        self.db.refresh(db_client)

        return self._to_domain(db_client)

    def update(self, client: DomainClient) -> DomainClient:
        """Update an existing client from domain entity."""
        if not client.id:
            raise ValueError("Client ID is required for update")

        db_client = self.db.query(DbClient).filter_by(id=client.id).first()
        if not db_client:
            raise ValueError(f"Client with ID {client.id} not found")

        # Update fields from domain entity using setattr to avoid type issues
        setattr(db_client, "name", str(client.full_name))
        setattr(db_client, "jotform_submission_id", str(client.jotform_submission_id))

        self.db.add(db_client)
        self.db.commit()
        self.db.refresh(db_client)

        return self._to_domain(db_client)

    def delete(self, client_id: int) -> bool:
        """Delete a client by ID."""
        db_client = self.db.query(DbClient).filter_by(id=client_id).first()
        if not db_client:
            return False

        self.db.delete(db_client)
        self.db.commit()
        return True

    def _to_domain(self, db_client: DbClient) -> DomainClient:
        """Convert database model to domain entity."""
        # Split stored name back into nome and sobrenome
        full_name = getattr(db_client, "name", "")
        name_parts = full_name.split(" ", 1) if full_name else ["", ""]
        primeiro_nome = name_parts[0] if len(name_parts) > 0 else ""
        sobrenome = name_parts[1] if len(name_parts) > 1 else ""

        return DomainClient(
            id=getattr(db_client, "id"),
            nome=primeiro_nome,
            sobrenome=sobrenome,
            jotform_submission_id=getattr(db_client, "jotform_submission_id"),
            created_at=getattr(db_client, "created_at", None),
            updated_at=getattr(db_client, "updated_at", None),
        )
