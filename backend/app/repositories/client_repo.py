"""Client repository implementation following SOLID principles.

Provides CRUD operations for Client domain entities while ensuring
display names are normalized before storage so UI dropdowns remain
consistent with the /clients page.
"""

from typing import Optional, List
from app.domain.interfaces import IClientRepository
from app.domain.entities import Client as DomainClient
from app.db.base import Client as DbClient
from app.utils.client_utils import normalize_display_name


class ClientRepository(IClientRepository):
    """Repository for Client persistence operations."""

    def __init__(self, db_session) -> None:
        self.db = db_session

    def _domain_full_name(self, client: DomainClient) -> str:
        """Extract full name from domain client, preferring full_name property."""
        full = getattr(client, "full_name", None)
        if full:
            return full
        nome = getattr(client, "nome", "") or ""
        sobrenome = getattr(client, "sobrenome", "") or ""
        return (nome + " " + sobrenome).strip()

    def get_by_id(self, client_id: int) -> Optional[DomainClient]:
        db_client = self.db.query(DbClient).filter_by(id=client_id).first()
        return self._to_domain(db_client) if db_client else None

    def get_all(self) -> List[DomainClient]:
        db_clients = self.db.query(DbClient).order_by(DbClient.name).all()
        domain_clients = [self._to_domain(c) for c in db_clients]
        return [c for c in domain_clients if c is not None]

    def get_by_jotform_id(self, jotform_id: str) -> Optional[DomainClient]:
        db_client = (
            self.db.query(DbClient).filter_by(jotform_submission_id=jotform_id).first()
        )
        return self._to_domain(db_client) if db_client else None

    def create(self, client: DomainClient) -> DomainClient:
        full_name = self._domain_full_name(client)
        stored_name = normalize_display_name(full_name)
        db_client = DbClient(
            name=stored_name,
            jotform_submission_id=str(getattr(client, "jotform_submission_id", "")),
        )
        self.db.add(db_client)
        self.db.commit()
        self.db.refresh(db_client)
        domain_client = self._to_domain(db_client)
        if domain_client is None:
            raise ValueError("Failed to create domain client from DB")
        return domain_client

    def update(self, client: DomainClient) -> DomainClient:
        if not getattr(client, "id", None):
            raise ValueError("Client ID is required for update")

        db_client = self.db.query(DbClient).filter_by(id=client.id).first()
        if not db_client:
            raise ValueError(f"Client with ID {client.id} not found")

        full_name = self._domain_full_name(client)
        db_client.name = normalize_display_name(full_name)
        db_client.jotform_submission_id = str(
            getattr(client, "jotform_submission_id", "")
        )
        self.db.add(db_client)
        self.db.commit()
        self.db.refresh(db_client)
        domain_client = self._to_domain(db_client)
        if domain_client is None:
            raise ValueError("Failed to update domain client from DB")
        return domain_client

    def delete(self, client_id: int) -> bool:
        db_client = self.db.query(DbClient).filter_by(id=client_id).first()
        if not db_client:
            return False
        self.db.delete(db_client)
        self.db.commit()
        return True

    def _to_domain(self, db_client: DbClient) -> Optional[DomainClient]:
        """Convert DB model to domain entity, splitting normalized name."""
        if not db_client:
            return None

        full_name = getattr(db_client, "name", "") or ""
        name_parts = full_name.split(" ", 1) if full_name else ["", ""]
        primeiro_nome = name_parts[0] if len(name_parts) > 0 else ""
        sobrenome = name_parts[1] if len(name_parts) > 1 else ""

        return DomainClient(
            id=getattr(db_client, "id", None),
            nome=primeiro_nome,
            sobrenome=sobrenome,
            jotform_submission_id=getattr(db_client, "jotform_submission_id", None),
            created_at=getattr(db_client, "created_at", None),
            updated_at=getattr(db_client, "updated_at", None),
        )
