from unittest.mock import patch

import pytest

# Ensure test imports are configured
from tests.config import setup_test_imports

setup_test_imports()


@pytest.mark.integration
def test_full_inventory_crud_flow(app, db_session, mock_authenticated_user):
    """End-to-end create/read/list/update/delete using the real app and DB."""
    # Create a test user in the database
    from app.db.base import User

    test_user = User(
        name="Test User",
        email="test@example.com",
        google_id="test123",
    )
    db_session.add(test_user)
    db_session.commit()
    db_session.refresh(test_user)

    with app.test_client() as client:
        with patch("flask_login.current_user", mock_authenticated_user):
            mock_authenticated_user.is_authenticated = True
            mock_authenticated_user.id = test_user.id

            with client.session_transaction() as sess:
                sess["user_id"] = test_user.id
                sess["_user_id"] = str(test_user.id)
                sess["logged_in"] = True

            # Create
            resp = client.post(
                "/inventory/", json={"nome": "Integration Test Item", "quantidade": 10}
            )
            assert resp.status_code == 201
            created = resp.get_json()
            item_id = created.get("id")
            assert item_id is not None

            # Read (the controller does not expose GET /inventory/<id> in this codebase),
            # so verify presence via list endpoint
            resp = client.get("/inventory/")
            assert resp.status_code == 200
            items = resp.get_json()
            assert any(item.get("id") == item_id for item in items)

            # Update
            resp = client.put(f"/inventory/{item_id}", json={"nome": "Updated Name"})
            assert resp.status_code == 200
            payload = resp.get_json()
            # update endpoint uses api_response(success, message, data)
            assert payload.get("success") is True
            assert payload.get("data", {}).get("nome") == "Updated Name"

            # Verify update via list
            resp = client.get("/inventory/")
            items = resp.get_json()
            assert any(
                item.get("id") == item_id and item.get("nome") == "Updated Name"
                for item in items
            )

            # Delete
            resp = client.delete(f"/inventory/{item_id}")
            assert resp.status_code == 200
    payload = resp.get_json()
    assert payload.get("success") is True

    # Verify deletion via list
    resp = client.get("/inventory/")
    items = resp.get_json()
    assert not any(item.get("id") == item_id for item in items)


@pytest.mark.integration
def test_change_quantity_flow(app, db_session, mock_authenticated_user):
    client = app.test_client()

    from app.db.base import User

    test_user = User(
        name="Inventory Tester",
        email="inventory@test.com",
        google_id="inventory123",
    )
    db_session.add(test_user)
    db_session.commit()
    db_session.refresh(test_user)

    with patch("flask_login.current_user", mock_authenticated_user):
        mock_authenticated_user.is_authenticated = True
        mock_authenticated_user.id = test_user.id

        with client.session_transaction() as sess:
            sess["user_id"] = test_user.id
            sess["_user_id"] = str(test_user.id)
            sess["logged_in"] = True

        # Create item with known quantity
        resp = client.post("/inventory/", json={"nome": "Qty Item", "quantidade": 10})
        assert resp.status_code == 201
        created = resp.get_json()
        item_id = created.get("id")

        # Increase quantity
        resp = client.patch(f"/inventory/{item_id}/quantity", json={"delta": 5})
        assert resp.status_code == 200
        updated = resp.get_json()
        assert updated.get("quantidade") == 15

        # Decrease quantity
        resp = client.patch(f"/inventory/{item_id}/quantity", json={"delta": -3})
        assert resp.status_code == 200
        updated = resp.get_json()
        assert updated.get("quantidade") == 12
