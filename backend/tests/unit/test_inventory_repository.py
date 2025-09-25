import pytest
# Ensure test import paths are set up like other tests
from tests.config import setup_test_imports

setup_test_imports()

from db.base import Inventory as InventoryModel
from domain.entities import InventoryItem
from repositories.inventory_repository import InventoryRepository


def make_item(nome="Test Item", quantidade=10, observacoes="note"):
    return InventoryItem(
        id=None, nome=nome, quantidade=quantidade, observacoes=observacoes
    )


def test_add_item_persists_and_returns_domain(db_session):
    repo = InventoryRepository(db_session)

    item = make_item()

    returned = repo.add(item)

    assert returned is not None
    assert getattr(returned, "id", None) is not None

    # verify persisted
    persisted = db_session.query(InventoryModel).get(returned.id)
    assert persisted is not None
    assert persisted.nome == item.nome
    assert persisted.quantidade == item.quantidade
    assert persisted.observacoes == item.observacoes


def test_get_by_id_returns_none_when_missing(db_session):
    repo = InventoryRepository(db_session)

    res = repo.get_by_id(999999)
    assert res is None


def test_get_by_id_returns_domain_when_found(db_session):
    repo = InventoryRepository(db_session)

    item = make_item()
    returned = repo.add(item)

    fetched = repo.get_by_id(returned.id)
    assert fetched is not None
    assert fetched.id == returned.id
    assert fetched.nome == returned.nome


def test_change_quantity_adjusts_value_and_returns_domain(db_session):
    repo = InventoryRepository(db_session)

    item = make_item(quantidade=10)
    returned = repo.add(item)

    updated = repo.change_quantity(returned.id, 5)
    assert updated.quantidade == 15

    # verify persisted change
    persisted = db_session.query(InventoryModel).get(returned.id)
    assert persisted.quantidade == 15
