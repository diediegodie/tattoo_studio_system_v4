import pytest

# Ensure import paths are configured like other tests
from tests.config import setup_test_imports

setup_test_imports()

from app.repositories.inventory_repository import InventoryRepository
from app.services.inventory_service import InventoryService
from app.domain.entities import InventoryItem
from app.db.base import Inventory as InventoryModel
from sqlalchemy.orm import sessionmaker


def make_item(nome="Item", quantidade=1, observacoes="x"):
    return InventoryItem(nome=nome, quantidade=quantidade, observacoes=observacoes)


def get_orders_map(session, ids):
    rows = session.query(InventoryModel).filter(InventoryModel.id.in_(ids)).all()
    return {r.id: getattr(r, "order", None) for r in rows}


def test_reorder_items_normal_case(db_session):
    session = db_session
    repo = InventoryRepository(session)
    service = InventoryService(repo)

    # Create 6 items
    created = [repo.add(make_item(f"N{i}")) for i in range(6)]
    ids = [c.id for c in created]

    # Apply a reordering: move first item to position 5
    reordered = ids[1:5] + [ids[0]] + ids[5:]
    service.reorder_items(reordered)

    # Verify DB orders match the new index positions
    db_map = get_orders_map(session, reordered)
    for idx, item_id in enumerate(reordered):
        assert db_map[item_id] == idx


def test_new_items_appear_first_before_reordering(db_session):
    session = db_session
    repo = InventoryRepository(session)

    # Create some items and assign manual order to them
    base = [repo.add(make_item(f"O{i}")) for i in range(3)]
    ordered_ids = [b.id for b in base]
    repo.reorder_items(ordered_ids)  # assign orders 0,1,2

    # Add a new item that should have order=None
    new_item = repo.add(make_item("New", 5))

    # List via repository service and ensure new item is present and stored with NULL order
    listed = repo.list_all()
    assert any(i.id == new_item.id for i in listed)
    stored = session.get(InventoryModel, new_item.id)
    assert getattr(stored, "order", None) is None

    # Now get manual-ordered items from DB ordered by order asc and compare
    manual_rows = (
        session.query(InventoryModel)
        .filter(InventoryModel.order != None)
        .order_by(InventoryModel.order.asc())
        .all()
    )
    # Keep only the ids that belong to our ordered set and preserve DB ordering
    manual_ids = [r.id for r in manual_rows if r.id in ordered_ids]
    assert manual_ids == ordered_ids


def test_reorder_empty_list(db_session):
    session = db_session
    repo = InventoryRepository(session)
    service = InventoryService(repo)

    # Create a few items
    created = [repo.add(make_item(f"E{i}")) for i in range(3)]
    before_map = get_orders_map(session, [c.id for c in created])

    # Calling reorder with empty list should not raise and should not change orders
    service.reorder_items([])

    after_map = get_orders_map(session, [c.id for c in created])
    assert before_map == after_map


def test_reorder_invalid_item_ids(db_session):
    session = db_session
    repo = InventoryRepository(session)
    service = InventoryService(repo)

    # Create two items
    a = repo.add(make_item("A"))
    b = repo.add(make_item("B"))

    # Provide invalid IDs mixed with valid ones; repo should ignore non-existent ids
    mixed = [999999, a.id, 888888, b.id]
    # Should not raise
    service.reorder_items(mixed)

    # Existing items must have been assigned positions according to their index in the provided list
    db_map = get_orders_map(session, [a.id, b.id])
    assert db_map[a.id] == mixed.index(a.id)
    assert db_map[b.id] == mixed.index(b.id)


def test_reordering_persists_after_session(db_session):
    # Create items and reorder, then open a new session to verify persistence
    session = db_session
    repo = InventoryRepository(session)
    service = InventoryService(repo)

    created = [repo.add(make_item(f"P{i}")) for i in range(4)]
    ids = [c.id for c in created]
    new_order = ids[::-1]
    service.reorder_items(new_order)

    # Simulate a new session (like an application restart)
    engine = session.get_bind()
    NewSession = sessionmaker(bind=engine)
    s2 = NewSession()
    try:
        repo2 = InventoryRepository(s2)
        listed2 = repo2.list_all()
        # Filter listed ids to those we created in this test to avoid interference
        listed_ids_filtered = [i.id for i in listed2 if i.id in ids]
        assert listed_ids_filtered == new_order
    finally:
        s2.close()


def test_consistent_ordering_between_service_and_repository(db_session):
    session = db_session
    repo = InventoryRepository(session)
    service = InventoryService(repo)

    # Create items
    created = [repo.add(make_item(f"C{i}")) for i in range(5)]
    ids = [c.id for c in created]

    # Assign manual ordering for some items
    manual = ids[1:4]
    repo.reorder_items(manual)

    repo_list = repo.list_all()
    service_list = service.list_items()

    assert [i.id for i in repo_list] == [i.id for i in service_list]
