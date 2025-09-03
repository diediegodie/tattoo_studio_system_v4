"""
Unit tests for ClientService following SOLID principles and existing test patterns.

This module tests the ClientService business logic with comprehensive coverage:
- Client retrieval operations
- JotForm synchronization
- Client creation and management
- Error handling and edge cases
"""

import pytest
from unittest.mock import Mock

# Test configuration and imports
from tests.config.test_paths import ensure_domain_imports

ensure_domain_imports()

try:
    from services.client_service import ClientService
    from tests.factories.repository_factories import (
        ClientRepositoryFactory,
        JotFormServiceFactory,
    )
    from domain.entities import Client as DomainClient

    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import required modules: {e}")
    IMPORTS_AVAILABLE = False


@pytest.fixture
def mock_client_repo() -> Mock:
    """Create a mock client repository."""
    return ClientRepositoryFactory.create_mock_full()


@pytest.fixture
def mock_jotform_service() -> Mock:
    """Create a mock JotForm service."""
    return JotFormServiceFactory.create_mock()


@pytest.fixture
def service(mock_client_repo, mock_jotform_service) -> ClientService:
    """Initialize ClientService with mocked dependencies."""
    return ClientService(mock_client_repo, mock_jotform_service)


@pytest.mark.unit
@pytest.mark.services
@pytest.mark.client
class TestClientServiceRetrieval:
    """Test client retrieval operations."""

    def test_get_all_clients_success(self, service, mock_client_repo):
        """Test successful retrieval of all clients."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock clients
        clients = [
            DomainClient(
                id=1, nome="João", sobrenome="Silva", jotform_submission_id="123"
            ),
            DomainClient(
                id=2, nome="Maria", sobrenome="Santos", jotform_submission_id="456"
            ),
        ]
        mock_client_repo.get_all.return_value = clients

        result = service.get_all_clients()

        assert result == clients
        mock_client_repo.get_all.assert_called_once()

    def test_get_client_by_id_success(self, service, mock_client_repo):
        """Test successful retrieval of client by ID."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        client_id = 1
        expected_client = DomainClient(
            id=client_id, nome="João", sobrenome="Silva", jotform_submission_id="123"
        )
        mock_client_repo.get_by_id.return_value = expected_client

        result = service.get_client_by_id(client_id)

        assert result == expected_client
        mock_client_repo.get_by_id.assert_called_once_with(client_id)

    def test_get_client_by_id_not_found(self, service, mock_client_repo):
        """Test client retrieval by ID when client doesn't exist."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        client_id = 999
        mock_client_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match=f"Client with ID {client_id} not found"):
            service.get_client_by_id(client_id)

        mock_client_repo.get_by_id.assert_called_once_with(client_id)


@pytest.mark.unit
@pytest.mark.services
@pytest.mark.client
class TestClientServiceJotFormSync:
    """Test JotForm synchronization functionality."""

    def test_sync_clients_from_jotform_success_new_clients(
        self, service, mock_client_repo, mock_jotform_service
    ):
        """Test successful synchronization of new clients from JotForm."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock JotForm submissions
        submissions = [
            {"id": "123", "client_name": "João Silva"},
            {"id": "456", "client_name": "Maria Santos"},
        ]
        mock_jotform_service.fetch_submissions.return_value = submissions

        # Mock parsing
        def mock_parse_name(submission):
            return submission["client_name"]

        mock_jotform_service.parse_client_name.side_effect = mock_parse_name

        # Mock repository - no existing clients
        mock_client_repo.get_by_jotform_id.return_value = None

        # Mock creation
        created_clients = [
            DomainClient(
                id=1, nome="João", sobrenome="Silva", jotform_submission_id="123"
            ),
            DomainClient(
                id=2, nome="Maria", sobrenome="Santos", jotform_submission_id="456"
            ),
        ]
        mock_client_repo.create.side_effect = created_clients

        result = service.sync_clients_from_jotform()

        assert len(result) == 2
        assert result == created_clients
        mock_jotform_service.fetch_submissions.assert_called_once()
        assert mock_client_repo.create.call_count == 2

    def test_sync_clients_from_jotform_skip_existing_clients(
        self, service, mock_client_repo, mock_jotform_service
    ):
        """Test that existing clients are skipped during synchronization."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock JotForm submissions
        submissions = [{"id": "123", "client_name": "João Silva"}]
        mock_jotform_service.fetch_submissions.return_value = submissions

        # Mock parsing
        mock_jotform_service.parse_client_name.return_value = "João Silva"

        # Mock repository - client already exists
        existing_client = DomainClient(
            id=1, nome="João", sobrenome="Silva", jotform_submission_id="123"
        )
        mock_client_repo.get_by_jotform_id.return_value = existing_client

        result = service.sync_clients_from_jotform()

        assert len(result) == 0  # No new clients created
        mock_jotform_service.fetch_submissions.assert_called_once()
        mock_client_repo.create.assert_not_called()

    def test_sync_clients_from_jotform_with_name_parsing(
        self, service, mock_client_repo, mock_jotform_service
    ):
        """Test client creation with proper name parsing."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock JotForm submissions with different name formats
        submissions = [
            {"id": "123", "client_name": "João Silva Santos"},  # First + Last
            {"id": "456", "client_name": "Maria"},  # Only first name
        ]
        mock_jotform_service.fetch_submissions.return_value = submissions

        # Mock parsing
        def mock_parse_name(submission):
            return submission["client_name"]

        mock_jotform_service.parse_client_name.side_effect = mock_parse_name

        # Mock repository - no existing clients
        mock_client_repo.get_by_jotform_id.return_value = None

        # Mock creation
        created_clients = [
            DomainClient(
                id=1, nome="João", sobrenome="Silva Santos", jotform_submission_id="123"
            ),
            DomainClient(id=2, nome="Maria", sobrenome="", jotform_submission_id="456"),
        ]
        mock_client_repo.create.side_effect = created_clients

        result = service.sync_clients_from_jotform()

        assert len(result) == 2
        assert result[0].nome == "João"
        assert result[0].sobrenome == "Silva Santos"
        assert result[1].nome == "Maria"
        assert result[1].sobrenome == ""

    def test_sync_clients_from_jotform_empty_submissions(
        self, service, mock_client_repo, mock_jotform_service
    ):
        """Test synchronization with empty submissions list."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock empty submissions
        mock_jotform_service.fetch_submissions.return_value = []

        result = service.sync_clients_from_jotform()

        assert len(result) == 0
        mock_jotform_service.fetch_submissions.assert_called_once()
        mock_client_repo.get_by_jotform_id.assert_not_called()
        mock_client_repo.create.assert_not_called()

    def test_sync_clients_from_jotform_repository_error(
        self, service, mock_client_repo, mock_jotform_service
    ):
        """Test synchronization when repository create fails."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock JotForm submissions
        submissions = [{"id": "123", "client_name": "João Silva"}]
        mock_jotform_service.fetch_submissions.return_value = submissions
        mock_jotform_service.parse_client_name.return_value = "João Silva"

        # Mock repository - no existing client, but create fails
        mock_client_repo.get_by_jotform_id.return_value = None
        mock_client_repo.create.return_value = None  # Simulate failure

        result = service.sync_clients_from_jotform()

        assert len(result) == 1
        assert result[0] is None  # Failed creation returns None


@pytest.mark.unit
@pytest.mark.services
@pytest.mark.client
class TestClientServiceJotFormDisplay:
    """Test JotForm display functionality."""

    def test_get_jotform_submissions_for_display_success(
        self, service, mock_jotform_service
    ):
        """Test successful retrieval of formatted submissions for display."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock submissions
        submissions = [
            {"id": "123", "status": "active", "client_name": "João Silva"},
            {"id": "456", "status": "pending", "client_name": "Maria Santos"},
        ]
        mock_jotform_service.fetch_submissions.return_value = submissions

        # Mock formatting
        formatted_data = [
            {"id": "123", "client_name": "João Silva", "status": "active"},
            {"id": "456", "client_name": "Maria Santos", "status": "pending"},
        ]

        def mock_format_data(submission):
            return {
                "id": submission["id"],
                "client_name": submission["client_name"],
                "status": submission["status"],
            }

        mock_jotform_service.format_submission_data.side_effect = mock_format_data

        result = service.get_jotform_submissions_for_display()

        assert len(result) == 2
        assert result == formatted_data
        mock_jotform_service.fetch_submissions.assert_called_once()
        assert mock_jotform_service.format_submission_data.call_count == 2

    def test_get_jotform_submissions_for_display_empty(
        self, service, mock_jotform_service
    ):
        """Test display retrieval with empty submissions."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock empty submissions
        mock_jotform_service.fetch_submissions.return_value = []

        result = service.get_jotform_submissions_for_display()

        assert len(result) == 0
        mock_jotform_service.fetch_submissions.assert_called_once()
        mock_jotform_service.format_submission_data.assert_not_called()
