from unittest.mock import Mock, patch

import pytest
# Ensure test imports are configured
from tests.config import setup_test_imports

setup_test_imports()

from importlib import import_module, reload

try:
    # Import domain entity (may raise in restricted environments)
    from app.domain.entities import InventoryItem

    DOMAIN_AVAILABLE = True
except Exception:
    DOMAIN_AVAILABLE = False


def import_inventory_controller_with_bypass():
    """Import the inventory_controller module while bypassing login_required."""
    with patch("flask_login.login_required", lambda f: f):
        mod = import_module("controllers.inventory_controller")
        # Ensure module is reloaded under the patched decorator
        reload(mod)
        return mod


try:
    inventory_controller = import_inventory_controller_with_bypass()
    IMPORTS_AVAILABLE = True
except Exception as e:
    print(f"Warning: Could not import inventory controller modules: {e}")
    IMPORTS_AVAILABLE = False


@pytest.fixture(autouse=True)
def mock_inventory_service():
    """Patch InventoryService used inside the controller to a Mock."""
    with patch("controllers.inventory_controller.InventoryService") as MockService:
        mock = Mock()
        MockService.return_value = mock
        yield mock


@pytest.fixture(autouse=True)
def bypass_login_required():
    """Patch the login_required decorator to a no-op so endpoints are callable in unit tests."""
    with patch("controllers.inventory_controller.login_required", lambda f: f):
        yield


@pytest.fixture
def local_client():
    """Create a local Flask app and register the inventory blueprint imported with bypass."""
    if not IMPORTS_AVAILABLE:
        pytest.skip("Inventory controller not importable")

    from flask import Flask

    app = Flask(__name__)
    app.register_blueprint(inventory_controller.inventory_bp)

    with app.test_client() as client:
        yield client


@pytest.mark.unit
@pytest.mark.controllers
class TestInventoryControllerEndpoints:
    def test_list_inventory_returns_200_and_json_array(
        self, login_client, mock_inventory_service
    ):
        if not IMPORTS_AVAILABLE:
            pytest.skip("Inventory controller not importable")

        # Mock the _get_user function to avoid database authentication
        from unittest.mock import MagicMock, patch

        from app.db.base import User

        mock_user = User(
            id=1, email="test@example.com", name="Test User", is_active=True
        )

        with patch("flask_login.utils._get_user", return_value=mock_user), patch(
            "app.controllers.inventory_controller.InventoryService"
        ) as MockService:
            mock_service = Mock()
            MockService.return_value = mock_service

            # Prepare mock return
            item = InventoryItem(id=1, nome="Ink", quantidade=10, observacoes="")
            mock_service.list_items.return_value = [item]

            resp = login_client.get("/inventory/")
            assert resp.status_code == 200
            data = resp.get_json()
            assert isinstance(data, list)
            assert data[0]["id"] == 1
            assert "nome" in data[0]

    def test_add_inventory_success_returns_201(
        self, login_client, mock_inventory_service
    ):
        if not IMPORTS_AVAILABLE:
            pytest.skip("Inventory controller not importable")

        # Mock the _get_user function to avoid database authentication
        from unittest.mock import MagicMock, patch

        from db.base import User

        mock_user = User(
            id=1, email="test@example.com", name="Test User", is_active=True
        )

        created = InventoryItem(id=2, nome="New Item", quantidade=5, observacoes="")
        mock_inventory_service.add_item.return_value = created

        with patch("flask_login.utils._get_user", return_value=mock_user), patch(
            "app.controllers.inventory_controller.SessionLocal"
        ) as mock_session, patch(
            "app.controllers.inventory_controller.InventoryRepository"
        ) as mock_repo_class, patch(
            "app.controllers.inventory_controller.InventoryService"
        ) as mock_service_class:

            # Setup mocks
            mock_db = MagicMock()
            mock_session.return_value = mock_db
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.add_item.return_value = created

            resp = login_client.post(
                "/inventory/", json={"nome": "New Item", "quantidade": 5}
            )
            assert resp.status_code == 201
            data = resp.get_json()
            assert data["id"] == 2
            assert data["nome"] == "New Item"

    def test_delete_inventory_returns_200(self, login_client, mock_inventory_service):
        if not IMPORTS_AVAILABLE:
            pytest.skip("Inventory controller not importable")

        # Mock the load_user function to avoid database authentication
        from unittest.mock import MagicMock, patch

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.name = "Test User"
        mock_user.is_active = True
        mock_user.is_authenticated = True
        mock_user.is_anonymous = False

        # Ensure the service reports the item exists
        mock_item = Mock()
        mock_item.id = 1
        mock_item.nome = "Ink"
        mock_item.quantidade = 10
        mock_item.observacoes = ""
        mock_inventory_service.get_item.return_value = mock_item

        with patch("flask_login.utils._get_user", return_value=mock_user), patch(
            "app.controllers.inventory_controller.SessionLocal"
        ) as mock_session, patch(
            "app.controllers.inventory_controller.InventoryRepository"
        ) as mock_repo_class, patch(
            "app.controllers.inventory_controller.InventoryService"
        ) as mock_service_class:

            # Setup mocks
            mock_db = MagicMock()
            mock_session.return_value = mock_db
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.get_item.return_value = mock_item

            resp = login_client.delete("/inventory/1")
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["success"] is True

    def test_change_quantity_returns_200(self, login_client, mock_inventory_service):
        if not IMPORTS_AVAILABLE:
            pytest.skip("Inventory controller not importable")

        # Mock the load_user function to avoid database authentication
        from unittest.mock import MagicMock, patch

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.name = "Test User"
        mock_user.is_active = True
        mock_user.is_authenticated = True
        mock_user.is_anonymous = False

        updated = Mock()
        updated.id = 1
        updated.nome = "Ink"
        updated.quantidade = 15
        updated.observacoes = ""
        updated.created_at = None
        updated.updated_at = None
        mock_inventory_service.change_quantity.return_value = updated

        with patch("flask_login.utils._get_user", return_value=mock_user), patch(
            "app.controllers.inventory_controller.SessionLocal"
        ) as mock_session, patch(
            "app.controllers.inventory_controller.InventoryRepository"
        ) as mock_repo_class, patch(
            "app.controllers.inventory_controller.InventoryService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.change_quantity.return_value = updated

            resp = login_client.patch("/inventory/1/quantity", json={"delta": 5})
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["quantidade"] == 15

    def test_update_inventory_item_returns_200(
        self, login_client, mock_inventory_service
    ):
        if not IMPORTS_AVAILABLE:
            pytest.skip("Inventory controller not importable")

        # Mock the load_user function to avoid database authentication
        from unittest.mock import MagicMock, patch

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.name = "Test User"
        mock_user.is_active = True
        mock_user.is_authenticated = True
        mock_user.is_anonymous = False

        updated = Mock()
        updated.id = 1
        updated.nome = "Updated Name"
        updated.quantidade = 5
        updated.observacoes = ""
        updated.created_at = None
        updated.updated_at = None
        mock_inventory_service.get_item.return_value = updated
        mock_inventory_service.update_item.return_value = updated

        with patch("flask_login.utils._get_user", return_value=mock_user), patch(
            "app.controllers.inventory_controller.SessionLocal"
        ) as mock_session, patch(
            "app.controllers.inventory_controller.InventoryRepository"
        ) as mock_repo_class, patch(
            "app.controllers.inventory_controller.InventoryService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            mock_service.get_item.return_value = updated
            mock_service.update_item.return_value = updated

            resp = login_client.put("/inventory/1", json={"nome": "Updated Name"})
            assert resp.status_code == 200
            data = resp.get_json()
            assert data["success"] is True
            assert data["data"]["nome"] == "Updated Name"
