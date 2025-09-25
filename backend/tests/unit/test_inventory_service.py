"""
Unit tests for InventoryService following SOLID and existing test patterns.

Tests use the repository mock factories and domain fixtures where possible.
"""

import sys
from pathlib import Path
from unittest.mock import Mock

import pytest
from tests.config import setup_test_imports

setup_test_imports()

from app.services.inventory_service import InventoryService
from domain.entities import InventoryItem as DomainInventoryItem
from tests.factories.repository_factories import InventoryRepositoryFactory


@pytest.fixture
def mock_repo() -> Mock:
    """Create a mock inventory repository implementing the interface."""
    mock = InventoryRepositoryFactory.create_mock_full()
    # The repository factory exposes `get_all` (interface name); the service expects
    # `list_all()` — alias for compatibility in tests.
    if not hasattr(mock, "list_all") and hasattr(mock, "get_all"):
        mock.list_all = mock.get_all
    # Factory uses `create` while concrete repository uses `add` - alias for tests
    if not hasattr(mock, "add") and hasattr(mock, "create"):
        mock.add = mock.create
    # Factory may expose update_stock instead of change_quantity
    if not hasattr(mock, "change_quantity") and hasattr(mock, "update_stock"):
        mock.change_quantity = mock.update_stock
    return mock


@pytest.fixture
def service(mock_repo) -> InventoryService:
    """Initialize InventoryService with mocked repository."""
    return InventoryService(mock_repo)


def test_list_items_returns_list_of_domain_entities(service, mock_repo):
    # Prepare two domain-like inventory items using the fixture helper class when available
    try:
        item1 = DomainInventoryItem(
            id=1,
            nome="Ink Black",
            quantidade=10,
            observacoes="",
            created_at=None,
            updated_at=None,
        )
        item2 = DomainInventoryItem(
            id=2,
            nome="Needles",
            quantidade=100,
            observacoes="Box of 100",
            created_at=None,
            updated_at=None,
        )
    except Exception:
        # Fallback simple objects if domain class not importable in CI
        item1 = Mock(id=1, nome="Ink Black", quantidade=10, observacoes="")
        item2 = Mock(id=2, nome="Needles", quantidade=100, observacoes="Box of 100")

    mock_repo.list_all.return_value = [item1, item2]

    result = service.list_items()

    assert result == [item1, item2]
    mock_repo.list_all.assert_called_once()


def test_add_item_calls_repository_and_returns_entity(service, mock_repo):
    # Prepare an input domain item (no ID yet)
    try:
        new_item = DomainInventoryItem(nome="New Ink", quantidade=20, observacoes="")
        created_item = DomainInventoryItem(
            id=10, nome="New Ink", quantidade=20, observacoes=""
        )
    except Exception:
        new_item = Mock(nome="New Ink", quantidade=20, observacoes="")
        created_item = Mock(id=10, nome="New Ink", quantidade=20, observacoes="")

    mock_repo.add.return_value = created_item

    result = service.add_item(new_item)

    assert result == created_item
    mock_repo.add.assert_called_once()
    # Validate that the service passed the same domain-like object to repository
    called_arg = mock_repo.add.call_args[0][0]
    assert hasattr(called_arg, "nome")


def test_update_item_success(service, mock_repo):
    try:
        item = DomainInventoryItem(
            id=5, nome="Needles", quantidade=90, observacoes="Box"
        )
        updated = DomainInventoryItem(
            id=5, nome="Needles", quantidade=95, observacoes="Box"
        )
    except Exception:
        item = Mock(id=5, nome="Needles", quantidade=90, observacoes="Box")
        updated = Mock(id=5, nome="Needles", quantidade=95, observacoes="Box")

    mock_repo.update.return_value = updated

    result = service.update_item(item)

    assert result == updated
    mock_repo.update.assert_called_once()


def test_update_item_handles_repository_exception(service, mock_repo):
    try:
        item = DomainInventoryItem(id=6, nome="Stencil", quantidade=5, observacoes="")
    except Exception:
        item = Mock(id=6, nome="Stencil", quantidade=5, observacoes="")

    mock_repo.update.side_effect = Exception("DB Error")
    # Pyright may complain about pytest.raises typing; silence for this context manager
    with pytest.raises(Exception, match="DB Error"):  # type: ignore
        service.update_item(item)


def test_change_quantity_updates_and_returns_item(service, mock_repo):
    try:
        updated = DomainInventoryItem(
            id=7, nome="Tattoo Ink", quantidade=12, observacoes=""
        )
    except Exception:
        updated = Mock(id=7, nome="Tattoo Ink", quantidade=12, observacoes="")

    mock_repo.change_quantity.return_value = updated

    result = service.change_quantity(7, 2)

    assert result == updated
    mock_repo.change_quantity.assert_called_once_with(7, 2)


def test_change_quantity_propagates_not_found(service, mock_repo):
    # Simulate repository raising when item not found
    mock_repo.change_quantity.side_effect = ValueError("Item not found")
    # Pyright may complain about pytest.raises typing; silence for this line
    with pytest.raises(ValueError, match="Item not found"):  # type: ignore
        service.change_quantity(999, 1)


def test_delete_item_calls_repository(service, mock_repo):
    service.delete_item(3)
    mock_repo.delete.assert_called_once_with(3)
