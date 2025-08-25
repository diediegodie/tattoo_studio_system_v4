import pytest

# Ensure imports/path setup for tests
from tests.config import setup_test_imports

setup_test_imports()


@pytest.mark.integration
def test_full_inventory_crud_flow(authenticated_client):
    """End-to-end create/read/list/update/delete using the real app and DB."""
    client = authenticated_client

    # Create
    resp = client.authenticated_post(
        "/inventory/", json={"nome": "Integration Test Item", "quantidade": 10}
    )
    assert resp.status_code == 201
    created = resp.get_json()
    item_id = created.get("id")
    assert item_id is not None

    # Read (the controller does not expose GET /inventory/<id> in this codebase),
    # so verify presence via list endpoint
    resp = client.authenticated_get("/inventory/")
    assert resp.status_code == 200
    items = resp.get_json()
    assert any(item.get("id") == item_id for item in items)

    # Update
    resp = client.authenticated_put(
        f"/inventory/{item_id}", json={"nome": "Updated Name"}
    )
    assert resp.status_code == 200
    payload = resp.get_json()
    # update endpoint uses api_response(success, message, data)
    assert payload.get("success") is True
    assert payload.get("data", {}).get("nome") == "Updated Name"

    # Verify update via list
    resp = client.authenticated_get("/inventory/")
    items = resp.get_json()
    assert any(
        item.get("id") == item_id and item.get("nome") == "Updated Name"
        for item in items
    )

    # Delete
    resp = client.authenticated_delete(f"/inventory/{item_id}")
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload.get("success") is True

    # Verify deletion via list
    resp = client.authenticated_get("/inventory/")
    items = resp.get_json()
    assert not any(item.get("id") == item_id for item in items)


@pytest.mark.integration
def test_change_quantity_flow(authenticated_client):
    client = authenticated_client

    # Create item with known quantity
    resp = client.authenticated_post(
        "/inventory/", json={"nome": "Qty Item", "quantidade": 10}
    )
    assert resp.status_code == 201
    created = resp.get_json()
    item_id = created.get("id")

    # Increase quantity
    resp = client.authenticated_patch(
        f"/inventory/{item_id}/quantity", json={"delta": 5}
    )
    assert resp.status_code == 200
    updated = resp.get_json()
    assert updated.get("quantidade") == 15

    # Decrease quantity
    resp = client.authenticated_patch(
        f"/inventory/{item_id}/quantity", json={"delta": -3}
    )
    assert resp.status_code == 200
    updated = resp.get_json()
    assert updated.get("quantidade") == 12
