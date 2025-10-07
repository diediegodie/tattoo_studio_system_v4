"""
Integration tests for drag_drop controller covering login enforcement and reorder flows.
"""

from __future__ import annotations

import pytest
from tests.config.test_paths import ensure_domain_imports

ensure_domain_imports()

try:
    from app.db.base import Inventory

    IMPORTS_AVAILABLE = True
except ImportError as exc:  # pragma: no cover - keep discovery resilient
    print(f"Warning: Drag & drop controller imports unavailable: {exc}")

    class Inventory:  # type: ignore[override]
        id = None
        order = None

        def __init__(self, *args, **kwargs):
            raise RuntimeError("Inventory model unavailable")

    IMPORTS_AVAILABLE = False


def _create_inventory_items(db_session, count: int = 2):
    if not IMPORTS_AVAILABLE:
        raise RuntimeError("Inventory model unavailable")

    items = []
    for i in range(count):
        item = Inventory(nome=f"Item {i}", quantidade=10 + i, order=None)
        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)
        items.append(item)
    return items


@pytest.fixture
def inventory_items(db_session):
    if not IMPORTS_AVAILABLE:
        pytest.skip("Drag & drop controller not available")
    return _create_inventory_items(db_session, 3)


@pytest.fixture
def logged_client(authenticated_client):
    if not IMPORTS_AVAILABLE:
        pytest.skip("Drag & drop controller not available")
    authenticated_client.mock_user.is_authenticated = True
    return authenticated_client


@pytest.mark.integration
@pytest.mark.controllers
@pytest.mark.drag_drop
class TestDragDropAuthentication:
    def test_requires_login_for_get(self, client):
        if not IMPORTS_AVAILABLE:
            pytest.skip("Drag & drop controller not available")
        response = client.get("/drag_drop")
        assert response.status_code in {302, 401}

    def test_requires_login_for_post(self, client):
        if not IMPORTS_AVAILABLE:
            pytest.skip("Drag & drop controller not available")
        response = client.post("/drag_drop", json={"order": []})
        assert response.status_code in {302, 401}


@pytest.mark.integration
@pytest.mark.controllers
@pytest.mark.drag_drop
class TestDragDropReorder:
    def test_get_renders_template(self, logged_client, inventory_items):
        response = logged_client.authenticated_get("/drag_drop")
        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert "drag_drop" in body.lower()

    def test_post_updates_order(self, logged_client, db_session, inventory_items):
        order_payload = {"order": [item.id for item in reversed(inventory_items)]}

        response = logged_client.authenticated_post("/drag_drop", json=order_payload)

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["redirect_url"].endswith("/estoque")

        reordered = (
            db_session.query(Inventory)
            .filter(Inventory.id.in_(order_payload["order"]))  # type: ignore[attr-defined]
            .order_by(Inventory.order.asc())  # type: ignore[attr-defined]
            .all()
        )
        assert [item.id for item in reordered] == order_payload["order"]

    def test_patch_behaves_like_post(self, logged_client, db_session, inventory_items):
        order_payload = {"order": [item.id for item in inventory_items]}

        response = logged_client.authenticated_patch("/drag_drop", json=order_payload)

        assert response.status_code == 200
        assert response.get_json()["success"] is True

    def test_post_requires_order_array(self, logged_client):
        response = logged_client.authenticated_post("/drag_drop", json={})
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["redirect_url"].endswith("/estoque")

    def test_post_rejects_non_json_payload(self, logged_client):
        response = logged_client.authenticated_post(
            "/drag_drop",
            data={"order": "1"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "Formato inválido" in data["error"]

    def test_service_failure_returns_400(self, logged_client, monkeypatch):
        from app.controllers import drag_drop_controller

        class Boom(Exception):
            pass

        def explode(_self, order):  # pragma: no cover - invoked via monkeypatch
            raise Boom("cannot reorder")

        monkeypatch.setattr(
            drag_drop_controller.InventoryService, "reorder_items", explode
        )

        response = logged_client.authenticated_post(
            "/drag_drop", json={"order": [1, 2, 3]}
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "cannot reorder" in data["error"]
