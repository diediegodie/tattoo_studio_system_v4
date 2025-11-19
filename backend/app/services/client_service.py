"""
Client service for business logic following SOLID principles.

This service:
- Keeps business rules separate from controllers and repositories (Single Responsibility)
- Depends on abstractions (IClientRepository, IJotFormService) not concrete implementations (Dependency Inversion)
- Can be easily extended without modification (Open/Closed)
- Works with domain entities, not database models
"""

from typing import Dict, List

from app.domain.entities import Client as DomainClient
from app.domain.interfaces import IClientRepository, IJotFormService


class ClientService:
    """Application service for client-related use-cases following SOLID principles."""

    def __init__(
        self, client_repo: IClientRepository, jotform_service: IJotFormService
    ) -> None:
        self.client_repo = client_repo
        self.jotform_service = jotform_service

    def get_all_clients(self) -> List[DomainClient]:
        """Get all clients from local database."""
        return self.client_repo.get_all()

    def sync_clients_from_jotform(self) -> List[DomainClient]:
        """Sync clients from JotForm and store in local database.

        Business Rules:
        - Sync all active submissions
        - Update existing clients with normalized names
        - Create new clients if they don't exist
        - Extract and normalize client name for database storage

        Performance Optimization:
        - Uses batch processing to avoid N+1 queries
        - Single commit at the end instead of per-client commits
        """
        submissions = self.jotform_service.fetch_submissions()

        # Batch fetch: Get all existing clients at once to avoid N+1 queries
        existing_clients_map = self.client_repo.get_all_by_jotform_ids(
            [str(s.get("id")) for s in submissions]
        )

        clients_to_create = []
        clients_to_update = []

        for submission in submissions:
            jotform_id = str(submission.get("id"))

            # Extract and normalize client name
            client_name = self.jotform_service.parse_client_name(submission)
            name_parts = client_name.split(" ", 1) if client_name else ["", ""]
            primeiro_nome = name_parts[0] if len(name_parts) > 0 else ""
            sobrenome = name_parts[1] if len(name_parts) > 1 else ""

            # Check if client already exists (from batch fetch)
            existing_client = existing_clients_map.get(jotform_id)
            if existing_client:
                # Update existing client with normalized name
                existing_client.nome = primeiro_nome
                existing_client.sobrenome = sobrenome
                clients_to_update.append(existing_client)
            else:
                # Prepare new client for batch creation
                new_client = DomainClient(
                    nome=primeiro_nome,
                    sobrenome=sobrenome,
                    jotform_submission_id=jotform_id,
                )
                clients_to_create.append(new_client)

        # Batch operations: Single commit for all changes
        synced_clients = self.client_repo.batch_create_and_update(
            clients_to_create, clients_to_update
        )

        return synced_clients

    def get_jotform_submissions_for_display(self) -> List[Dict]:
        """Get formatted JotForm submissions for display in the UI.

        This returns ALL submission data for the client list page,
        while only storing client names in the database.
        """
        submissions = self.jotform_service.fetch_submissions()
        formatted_submissions = []

        for submission in submissions:
            formatted_data = self.jotform_service.format_submission_data(submission)
            formatted_submissions.append(formatted_data)

        return formatted_submissions

    def get_client_by_id(self, client_id: int) -> DomainClient:
        """Get a specific client by ID."""
        client = self.client_repo.get_by_id(client_id)
        if not client:
            raise ValueError(f"Client with ID {client_id} not found")
        return client
