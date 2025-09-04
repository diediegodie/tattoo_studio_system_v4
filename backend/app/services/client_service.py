"""
Client service for business logic following SOLID principles.

This service:
- Keeps business rules separate from controllers and repositories (Single Responsibility)
- Depends on abstractions (IClientRepository, IJotFormService) not concrete implementations (Dependency Inversion)
- Can be easily extended without modification (Open/Closed)
- Works with domain entities, not database models
"""

from typing import List, Dict
from app.domain.interfaces import IClientRepository, IJotFormService
from app.domain.entities import Client as DomainClient


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
        - Only sync active submissions
        - Don't duplicate existing clients
        - Extract only client name for database storage
        """
        submissions = self.jotform_service.fetch_submissions()
        synced_clients = []

        for submission in submissions:
            jotform_id = str(submission.get("id"))

            # Check if client already exists
            existing_client = self.client_repo.get_by_jotform_id(jotform_id)
            if existing_client:
                continue  # Skip if already exists

            # Extract client name
            client_name = self.jotform_service.parse_client_name(submission)

            # Create new client - split name into nome and sobrenome
            name_parts = client_name.split(" ", 1) if client_name else ["", ""]
            primeiro_nome = name_parts[0] if len(name_parts) > 0 else ""
            sobrenome = name_parts[1] if len(name_parts) > 1 else ""

            # Create new client
            new_client = DomainClient(
                nome=primeiro_nome,
                sobrenome=sobrenome,
                jotform_submission_id=jotform_id,
            )

            created_client = self.client_repo.create(new_client)
            synced_clients.append(created_client)

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
