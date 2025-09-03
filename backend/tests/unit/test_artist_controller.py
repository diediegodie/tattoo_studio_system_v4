"""
Unit tests for ArtistController following SOLID principles and existing test patterns.

This module tests the ArtistController HTTP layer with comprehensive coverage:
- Artist creation via JSON and form endpoints
- Artist listing
- Input validation and error handling
- Service layer integration
- Response format consistency
"""

import pytest
import json
from unittest.mock import Mock, patch

# Test configuration and imports
from tests.config.test_paths import ensure_domain_imports

ensure_domain_imports()

try:
    from controllers import artist_controller
    from services.user_service import UserService
    from domain.entities import User as DomainUser

    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import required modules: {e}")
    IMPORTS_AVAILABLE = False


@pytest.mark.unit
@pytest.mark.controllers
@pytest.mark.artist
class TestArtistControllerCreate:
    """Test artist creation endpoints."""

    def test_create_artist_success_with_email(self, client, app):
        """Test successful artist creation with email via JSON."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock the service
        with patch(
            "controllers.artist_controller.UserService"
        ) as mock_user_service_class, patch(
            "controllers.artist_controller.UserRepository"
        ) as mock_user_repo_class, patch(
            "controllers.artist_controller.SessionLocal"
        ) as mock_session_local:

            # Set up the mocks
            mock_session = Mock()
            mock_session_local.return_value = mock_session

            mock_repo = Mock()
            mock_user_repo_class.return_value = mock_repo

            mock_service = Mock()
            mock_user_service_class.return_value = mock_service

            mock_artist = Mock()
            mock_artist.id = 1
            mock_artist.name = "John Artist"
            mock_artist.email = "john.artist@example.com"
            mock_artist.role = "artist"
            mock_artist.is_active = True
            mock_service.register_artist.return_value = mock_artist
            mock_user_service_class.return_value = mock_service

            mock_artist = Mock()
            mock_artist.id = 1
            mock_artist.name = "John Artist"
            mock_artist.email = "john.artist@example.com"
            mock_artist.role = "artist"
            mock_artist.is_active = True
            mock_service.register_artist.return_value = mock_artist

            # Test the endpoint
            response = client.post(
                "/artist/create",
                json={"name": "John Artist", "email": "john.artist@example.com"},
                content_type="application/json",
            )

            assert response.status_code == 201
            data = json.loads(response.data)
            assert data["success"] is True
            assert data["artist"]["name"] == "John Artist"
            mock_service.register_artist.assert_called_once_with(
                name="John Artist", email="john.artist@example.com"
            )

    def test_create_artist_success_without_email(self, client, app):
        """Test successful artist creation without email via JSON."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock the service
        with patch(
            "controllers.artist_controller._get_user_service"
        ) as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service

            mock_artist = Mock()
            mock_artist.id = 2
            mock_artist.name = "Jane Artist"
            mock_artist.email = ""
            mock_artist.role = "artist"
            mock_artist.is_active = True
            mock_service.register_artist.return_value = mock_artist

            # Test the endpoint
            response = client.post(
                "/artist/create",
                json={"name": "Jane Artist"},
                content_type="application/json",
            )

            assert response.status_code == 201
            data = json.loads(response.data)
            assert data["success"] is True
            mock_service.register_artist.assert_called_once_with(
                name="Jane Artist", email=None
            )

    def test_create_artist_invalid_content_type(self, client, app):
        """Test artist creation with invalid content type."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Test with invalid content type
        response = client.post(
            "/artist/create", data="invalid data", content_type="text/plain"
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Content-Type must be application/json" in data["error"]

    def test_create_artist_missing_body(self, client, app):
        """Test artist creation with missing request body."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Test with empty JSON
        response = client.post(
            "/artist/create", json={}, content_type="application/json"
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Request body is required" in data["error"]

    def test_create_artist_missing_name(self, client, app):
        """Test artist creation with missing name."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Test with missing name
        response = client.post(
            "/artist/create",
            json={"email": "artist@example.com"},
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Artist name is required" in data["error"]

    def test_create_artist_empty_name(self, client, app):
        """Test artist creation with empty name."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Test with empty name
        response = client.post(
            "/artist/create", json={"name": ""}, content_type="application/json"
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Artist name is required" in data["error"]

    def test_create_artist_service_validation_error(self, client, app):
        """Test artist creation with service validation error."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock the service to raise ValueError
        with patch(
            "controllers.artist_controller._get_user_service"
        ) as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.register_artist.side_effect = ValueError(
                "Email already exists"
            )

            response = client.post(
                "/artist/create",
                json={"name": "John Artist", "email": "existing@example.com"},
                content_type="application/json",
            )

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Email already exists" in data["error"]

    def test_create_artist_unexpected_error(self, client, app):
        """Test artist creation with unexpected error."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock the service to raise unexpected error
        with patch(
            "controllers.artist_controller._get_user_service"
        ) as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.register_artist.side_effect = Exception("Database error")

            response = client.post(
                "/artist/create",
                json={"name": "John Artist"},
                content_type="application/json",
            )

            assert response.status_code == 500
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Internal server error" in data["error"]


@pytest.mark.unit
@pytest.mark.controllers
@pytest.mark.artist
class TestArtistControllerList:
    """Test artist listing endpoints."""

    def test_list_artists_success(self, client, app):
        """Test successful artist listing."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock the service
        with patch(
            "controllers.artist_controller._get_user_service"
        ) as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service

            mock_artists = [
                Mock(
                    id=1,
                    name="Artist One",
                    email="one@example.com",
                    role="artist",
                    is_active=True,
                ),
                Mock(
                    id=2,
                    name="Artist Two",
                    email="two@example.com",
                    role="artist",
                    is_active=True,
                ),
            ]
            mock_service.list_artists.return_value = mock_artists

            # Test the endpoint
            response = client.get("/artist/list")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert len(data["artists"]) == 2
            assert data["artists"][0]["name"] == "Artist One"
            mock_service.list_artists.assert_called_once()

    def test_list_artists_empty(self, client, app):
        """Test artist listing when no artists exist."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock the service with empty list
        with patch(
            "controllers.artist_controller._get_user_service"
        ) as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.list_artists.return_value = []

            response = client.get("/artist/list")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert data["artists"] == []

    def test_list_artists_unexpected_error(self, client, app):
        """Test artist listing with unexpected error."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock the service to raise error
        with patch(
            "controllers.artist_controller._get_user_service"
        ) as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.list_artists.side_effect = Exception("Database error")

            response = client.get("/artist/list")

            assert response.status_code == 500
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Internal server error" in data["error"]


@pytest.mark.unit
@pytest.mark.controllers
@pytest.mark.artist
class TestArtistControllerForm:
    """Test artist creation from form data."""

    def test_create_artist_form_success_with_name_field(self, client, app):
        """Test successful artist creation from form with 'name' field."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock the service
        with patch(
            "controllers.artist_controller._get_user_service"
        ) as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service

            mock_artist = Mock()
            mock_artist.id = 3
            mock_artist.name = "Form Artist"
            mock_artist.email = "form@example.com"
            mock_artist.role = "artist"
            mock_artist.is_active = True
            mock_service.register_artist.return_value = mock_artist

            # Test the endpoint with form data
            response = client.post(
                "/artist/create_form",
                data={"name": "Form Artist", "email": "form@example.com"},
                content_type="application/x-www-form-urlencoded",
            )

            assert response.status_code == 201
            data = json.loads(response.data)
            assert data["success"] is True
            mock_service.register_artist.assert_called_once_with(
                name="Form Artist", email="form@example.com"
            )

    def test_create_artist_form_success_with_artista_field(self, client, app):
        """Test successful artist creation from form with 'artista' field."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock the service
        with patch(
            "controllers.artist_controller._get_user_service"
        ) as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service

            mock_artist = Mock()
            mock_artist.id = 4
            mock_artist.name = "Legacy Artist"
            mock_artist.email = "legacy@example.com"
            mock_artist.role = "artist"
            mock_artist.is_active = True
            mock_service.register_artist.return_value = mock_artist

            # Test the endpoint with 'artista' field
            response = client.post(
                "/artist/create_form",
                data={"artista": "Legacy Artist", "email": "legacy@example.com"},
                content_type="application/x-www-form-urlencoded",
            )

            assert response.status_code == 201
            data = json.loads(response.data)
            assert data["success"] is True
            mock_service.register_artist.assert_called_once_with(
                name="Legacy Artist", email="legacy@example.com"
            )

    def test_create_artist_form_missing_name(self, client, app):
        """Test artist creation from form with missing name."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Test with no name fields
        response = client.post(
            "/artist/create_form",
            data={"email": "test@example.com"},
            content_type="application/x-www-form-urlencoded",
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Artist name is required" in data["error"]

    def test_create_artist_form_service_validation_error(self, client, app):
        """Test artist creation from form with service validation error."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock the service to raise ValueError
        with patch(
            "controllers.artist_controller._get_user_service"
        ) as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service
            mock_service.register_artist.side_effect = ValueError(
                "Email already registered"
            )

            response = client.post(
                "/artist/create_form",
                data={"name": "Duplicate Artist", "email": "duplicate@example.com"},
                content_type="application/x-www-form-urlencoded",
            )

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data["success"] is False
            assert "Email already registered" in data["error"]


@pytest.mark.unit
@pytest.mark.controllers
@pytest.mark.artist
class TestArtistControllerDependencyInjection:
    """Test dependency injection and service creation."""

    def test_get_user_service_creates_dependencies(self):
        """Test that _get_user_service creates all required dependencies."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        with patch(
            "controllers.artist_controller.SessionLocal"
        ) as mock_session_local, patch(
            "controllers.artist_controller.UserRepository"
        ) as mock_user_repo, patch(
            "controllers.artist_controller.UserService"
        ) as mock_user_service:

            # Mock session
            mock_session = Mock()
            mock_session_local.return_value = mock_session

            # Mock repository and service
            mock_repo_instance = Mock()
            mock_user_repo.return_value = mock_repo_instance

            mock_service_instance = Mock()
            mock_user_service.return_value = mock_service_instance

            result = artist_controller._get_user_service()

            assert result == mock_service_instance
            mock_session_local.assert_called_once()
            mock_user_repo.assert_called_once_with(mock_session)
            mock_user_service.assert_called_once_with(mock_repo_instance)


import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# Test configuration and imports
from tests.config.test_paths import ensure_domain_imports

ensure_domain_imports()

try:
    from controllers import artist_controller
    from app.services.user_service import UserService
    from app.domain.entities import User as DomainUser

    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import required modules: {e}")
    IMPORTS_AVAILABLE = False


@pytest.mark.unit
@pytest.mark.controllers
@pytest.mark.artist
class TestArtistControllerCreate:
    """Test artist creation endpoints."""

    @patch("controllers.artist_controller._get_user_service")
    @patch("controllers.artist_controller.request")
    def test_create_artist_success_with_email(self, mock_request, mock_get_service):
        """Test successful artist creation with email via JSON."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock request
        mock_request.is_json = True
        mock_request.get_json.return_value = {
            "name": "John Artist",
            "email": "john.artist@example.com",
        }

        # Mock service and artist
        mock_service = Mock()
        mock_get_service.return_value = mock_service

        mock_artist = DomainUser(
            id=1,
            name="John Artist",
            email="john.artist@example.com",
            role="artist",
            is_active=True,
        )
        mock_service.register_artist.return_value = mock_artist

        # Mock jsonify and response
        with patch("controllers.artist_controller.jsonify") as mock_jsonify:
            mock_response = Mock()
            mock_jsonify.return_value = mock_response

            result, status_code = artist_controller.create_artist()

            assert status_code == 201
            mock_service.register_artist.assert_called_once_with(
                name="John Artist", email="john.artist@example.com"
            )
            mock_jsonify.assert_called_once()
            call_args = mock_jsonify.call_args[0][0]
            assert call_args["success"] is True
            assert call_args["artist"]["name"] == "John Artist"

    @patch("controllers.artist_controller._get_user_service")
    @patch("controllers.artist_controller.request")
    def test_create_artist_success_without_email(self, mock_request, mock_get_service):
        """Test successful artist creation without email via JSON."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock request
        mock_request.is_json = True
        mock_request.get_json.return_value = {"name": "Jane Artist"}

        # Mock service and artist
        mock_service = Mock()
        mock_get_service.return_value = mock_service

        mock_artist = DomainUser(
            id=2, name="Jane Artist", email="", role="artist", is_active=True
        )
        mock_service.register_artist.return_value = mock_artist

        with patch("controllers.artist_controller.jsonify") as mock_jsonify:
            mock_response = Mock()
            mock_jsonify.return_value = mock_response

            result, status_code = artist_controller.create_artist()

            assert status_code == 201
            mock_service.register_artist.assert_called_once_with(
                name="Jane Artist", email=None
            )

    @patch("controllers.artist_controller.request")
    def test_create_artist_invalid_content_type(self, mock_request):
        """Test artist creation with invalid content type."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock request with invalid content type
        mock_request.is_json = False

        with patch("controllers.artist_controller.jsonify") as mock_jsonify:
            mock_response = Mock()
            mock_jsonify.return_value = mock_response

            result, status_code = artist_controller.create_artist()

            assert status_code == 400
            mock_jsonify.assert_called_once_with(
                {"success": False, "error": "Content-Type must be application/json"}
            )

    @patch("controllers.artist_controller.request")
    def test_create_artist_missing_body(self, mock_request):
        """Test artist creation with missing request body."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock request with no JSON body
        mock_request.is_json = True
        mock_request.get_json.return_value = None

        with patch("controllers.artist_controller.jsonify") as mock_jsonify:
            mock_response = Mock()
            mock_jsonify.return_value = mock_response

            result, status_code = artist_controller.create_artist()

            assert status_code == 400
            mock_jsonify.assert_called_once_with(
                {"success": False, "error": "Request body is required"}
            )

    @patch("controllers.artist_controller.request")
    def test_create_artist_missing_name(self, mock_request):
        """Test artist creation with missing name."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock request with missing name
        mock_request.is_json = True
        mock_request.get_json.return_value = {"email": "artist@example.com"}

        with patch("controllers.artist_controller.jsonify") as mock_jsonify:
            mock_response = Mock()
            mock_jsonify.return_value = mock_response

            result, status_code = artist_controller.create_artist()

            assert status_code == 400
            mock_jsonify.assert_called_once_with(
                {"success": False, "error": "Artist name is required"}
            )

    @patch("controllers.artist_controller.request")
    def test_create_artist_empty_name(self, mock_request):
        """Test artist creation with empty name."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock request with empty name
        mock_request.is_json = True
        mock_request.get_json.return_value = {"name": ""}

        with patch("controllers.artist_controller.jsonify") as mock_jsonify:
            mock_response = Mock()
            mock_jsonify.return_value = mock_response

            result, status_code = artist_controller.create_artist()

            assert status_code == 400
            mock_jsonify.assert_called_once_with(
                {"success": False, "error": "Artist name is required"}
            )

    @patch("controllers.artist_controller._get_user_service")
    @patch("controllers.artist_controller.request")
    def test_create_artist_service_validation_error(
        self, mock_request, mock_get_service
    ):
        """Test artist creation with service validation error."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock request
        mock_request.is_json = True
        mock_request.get_json.return_value = {
            "name": "John Artist",
            "email": "existing@example.com",
        }

        # Mock service to raise ValueError
        mock_service = Mock()
        mock_get_service.return_value = mock_service
        mock_service.register_artist.side_effect = ValueError("Email already exists")

        with patch("controllers.artist_controller.jsonify") as mock_jsonify:
            mock_response = Mock()
            mock_jsonify.return_value = mock_response

            result, status_code = artist_controller.create_artist()

            assert status_code == 400
            mock_jsonify.assert_called_once_with(
                {"success": False, "error": "Email already exists"}
            )

    @patch("controllers.artist_controller._get_user_service")
    @patch("controllers.artist_controller.request")
    def test_create_artist_unexpected_error(self, mock_request, mock_get_service):
        """Test artist creation with unexpected error."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock request
        mock_request.is_json = True
        mock_request.get_json.return_value = {"name": "John Artist"}

        # Mock service to raise unexpected error
        mock_service = Mock()
        mock_get_service.return_value = mock_service
        mock_service.register_artist.side_effect = Exception("Database error")

        with patch("controllers.artist_controller.jsonify") as mock_jsonify:
            mock_response = Mock()
            mock_jsonify.return_value = mock_response

            result, status_code = artist_controller.create_artist()

            assert status_code == 500
            mock_jsonify.assert_called_once_with(
                {"success": False, "error": "Internal server error"}
            )


@pytest.mark.unit
@pytest.mark.controllers
@pytest.mark.artist
class TestArtistControllerList:
    """Test artist listing endpoints."""

    @patch("controllers.artist_controller._get_user_service")
    def test_list_artists_success(self, mock_get_service):
        """Test successful artist listing."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock service and artists
        mock_service = Mock()
        mock_get_service.return_value = mock_service

        mock_artists = [
            DomainUser(
                id=1,
                name="Artist One",
                email="one@example.com",
                role="artist",
                is_active=True,
            ),
            DomainUser(
                id=2,
                name="Artist Two",
                email="two@example.com",
                role="artist",
                is_active=True,
            ),
        ]
        mock_service.list_artists.return_value = mock_artists

        with patch("controllers.artist_controller.jsonify") as mock_jsonify:
            mock_response = Mock()
            mock_jsonify.return_value = mock_response

            result, status_code = artist_controller.list_artists()

            assert status_code == 200
            mock_service.list_artists.assert_called_once()
            mock_jsonify.assert_called_once()
            call_args = mock_jsonify.call_args[0][0]
            assert call_args["success"] is True
            assert len(call_args["artists"]) == 2
            assert call_args["artists"][0]["name"] == "Artist One"

    @patch("controllers.artist_controller._get_user_service")
    def test_list_artists_empty(self, mock_get_service):
        """Test artist listing when no artists exist."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock service with empty list
        mock_service = Mock()
        mock_get_service.return_value = mock_service
        mock_service.list_artists.return_value = []

        with patch("controllers.artist_controller.jsonify") as mock_jsonify:
            mock_response = Mock()
            mock_jsonify.return_value = mock_response

            result, status_code = artist_controller.list_artists()

            assert status_code == 200
            mock_jsonify.assert_called_once()
            call_args = mock_jsonify.call_args[0][0]
            assert call_args["success"] is True
            assert call_args["artists"] == []

    @patch("controllers.artist_controller._get_user_service")
    def test_list_artists_unexpected_error(self, mock_get_service):
        """Test artist listing with unexpected error."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock service to raise error
        mock_service = Mock()
        mock_get_service.return_value = mock_service
        mock_service.list_artists.side_effect = Exception("Database error")

        with patch("controllers.artist_controller.jsonify") as mock_jsonify:
            mock_response = Mock()
            mock_jsonify.return_value = mock_response

            result, status_code = artist_controller.list_artists()

            assert status_code == 500
            mock_jsonify.assert_called_once_with(
                {"success": False, "error": "Internal server error"}
            )


@pytest.mark.unit
@pytest.mark.controllers
@pytest.mark.artist
class TestArtistControllerForm:
    """Test artist creation from form data."""

    @patch("controllers.artist_controller._get_user_service")
    @patch("controllers.artist_controller.request")
    def test_create_artist_form_success_with_name_field(
        self, mock_request, mock_get_service
    ):
        """Test successful artist creation from form with 'name' field."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock form request
        mock_request.form.get.side_effect = lambda key: {
            "name": "Form Artist",
            "email": "form@example.com",
        }.get(key)

        # Mock service and artist
        mock_service = Mock()
        mock_get_service.return_value = mock_service

        mock_artist = DomainUser(
            id=3,
            name="Form Artist",
            email="form@example.com",
            role="artist",
            is_active=True,
        )
        mock_service.register_artist.return_value = mock_artist

        with patch("controllers.artist_controller.jsonify") as mock_jsonify:
            mock_response = Mock()
            mock_jsonify.return_value = mock_response

            result, status_code = artist_controller.create_artist_form()

            assert status_code == 201
            mock_service.register_artist.assert_called_once_with(
                name="Form Artist", email="form@example.com"
            )

    @patch("controllers.artist_controller._get_user_service")
    @patch("controllers.artist_controller.request")
    def test_create_artist_form_success_with_artista_field(
        self, mock_request, mock_get_service
    ):
        """Test successful artist creation from form with 'artista' field."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock form request with 'artista' field
        mock_request.form.get.side_effect = lambda key: {
            "artista": "Legacy Artist",
            "email": "legacy@example.com",
        }.get(key)

        # Mock service and artist
        mock_service = Mock()
        mock_get_service.return_value = mock_service

        mock_artist = DomainUser(
            id=4,
            name="Legacy Artist",
            email="legacy@example.com",
            role="artist",
            is_active=True,
        )
        mock_service.register_artist.return_value = mock_artist

        with patch("controllers.artist_controller.jsonify") as mock_jsonify:
            mock_response = Mock()
            mock_jsonify.return_value = mock_response

            result, status_code = artist_controller.create_artist_form()

            assert status_code == 201
            mock_service.register_artist.assert_called_once_with(
                name="Legacy Artist", email="legacy@example.com"
            )

    @patch("controllers.artist_controller.request")
    def test_create_artist_form_missing_name(self, mock_request):
        """Test artist creation from form with missing name."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock form request with no name fields
        mock_request.form.get.return_value = None

        with patch("controllers.artist_controller.jsonify") as mock_jsonify:
            mock_response = Mock()
            mock_jsonify.return_value = mock_response

            result, status_code = artist_controller.create_artist_form()

            assert status_code == 400
            mock_jsonify.assert_called_once_with(
                {"success": False, "error": "Artist name is required"}
            )

    @patch("controllers.artist_controller._get_user_service")
    @patch("controllers.artist_controller.request")
    def test_create_artist_form_service_validation_error(
        self, mock_request, mock_get_service
    ):
        """Test artist creation from form with service validation error."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock form request
        mock_request.form.get.side_effect = lambda key: {
            "name": "Duplicate Artist",
            "email": "duplicate@example.com",
        }.get(key)

        # Mock service to raise ValueError
        mock_service = Mock()
        mock_get_service.return_value = mock_service
        mock_service.register_artist.side_effect = ValueError(
            "Email already registered"
        )

        with patch("controllers.artist_controller.jsonify") as mock_jsonify:
            mock_response = Mock()
            mock_jsonify.return_value = mock_response

            result, status_code = artist_controller.create_artist_form()

            assert status_code == 400
            mock_jsonify.assert_called_once_with(
                {"success": False, "error": "Email already registered"}
            )


@pytest.mark.unit
@pytest.mark.controllers
@pytest.mark.artist
class TestArtistControllerDependencyInjection:
    """Test dependency injection and service creation."""

    @patch("controllers.artist_controller.SessionLocal")
    @patch("controllers.artist_controller.UserRepository")
    @patch("controllers.artist_controller.UserService")
    def test_get_user_service_creates_dependencies(
        self, mock_user_service, mock_user_repo, mock_session_local
    ):
        """Test that _get_user_service creates all required dependencies."""
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        # Mock session
        mock_session = Mock()
        mock_session_local.return_value = mock_session

        # Mock repository and service
        mock_repo_instance = Mock()
        mock_user_repo.return_value = mock_repo_instance

        mock_service_instance = Mock()
        mock_user_service.return_value = mock_service_instance

        result = artist_controller._get_user_service()

        assert result == mock_service_instance
        mock_session_local.assert_called_once()
        mock_user_repo.assert_called_once_with(mock_session)
        mock_user_service.assert_called_once_with(mock_repo_instance)
