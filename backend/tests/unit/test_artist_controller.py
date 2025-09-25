"""
Consolidated unit tests for ArtistController.
Uses the Flask `client` fixture and patches the controller's service factory
so tests run inside request/app context and avoid 'Working outside of request context' errors.
"""

import json
from dataclasses import dataclass
from typing import Any
from unittest.mock import Mock, patch

import pytest
from tests.config.test_paths import ensure_domain_imports

ensure_domain_imports()
try:
    from app.controllers import artist_controller
    from app.domain.entities import User as DomainUser

    IMPORTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import required modules: {e}")
    # Provide safe fallbacks so static analyzers and later guards work
    artist_controller: Any = None
    DomainUser: Any = None
    IMPORTS_AVAILABLE = False
    IMPORTS_AVAILABLE = False


@dataclass
class MockArtist:
    id: int
    name: str
    email: str
    role: str = "artist"


@pytest.mark.unit
@pytest.mark.controllers
@pytest.mark.artist
class TestArtistControllerEndpoints:
    def test_create_artist_success_with_email(self, client, app):
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        with patch(
            "app.controllers.artist_controller._get_user_service"
        ) as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service

            mock_artist = MockArtist(
                id=1, name="John Artist", email="john.artist@example.com", role="artist"
            )
            mock_service.register_artist.return_value = mock_artist

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

    def test_create_artist_missing_name(self, client, app):
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        response = client.post(
            "/artist/create",
            json={"email": "artist@example.com"},
            content_type="application/json",
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data["success"] is False
        assert "Artist name is required" in data["error"]

    def test_list_artists_success(self, client, app):
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        with patch(
            "app.controllers.artist_controller._get_user_service"
        ) as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service

            mock_artists = [
                MockArtist(id=1, name="Artist One", email="one@example.com"),
                MockArtist(id=2, name="Artist Two", email="two@example.com"),
            ]
            mock_service.list_artists.return_value = mock_artists

            response = client.get("/artist/list")

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data["success"] is True
            assert len(data["artists"]) == 2
            assert data["artists"][0]["name"] == "Artist One"

    def test_create_artist_form_success_with_name_field(self, client, app):
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        with patch(
            "app.controllers.artist_controller._get_user_service"
        ) as mock_get_service:
            mock_service = Mock()
            mock_get_service.return_value = mock_service

            mock_artist = MockArtist(id=3, name="Form Artist", email="form@example.com")
            mock_service.register_artist.return_value = mock_artist

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


@pytest.mark.unit
@pytest.mark.controllers
@pytest.mark.artist
class TestArtistControllerDI:
    def test_get_user_service_creates_dependencies(self):
        if not IMPORTS_AVAILABLE:
            pytest.skip("Required modules not available")

        with patch(
            "app.controllers.artist_controller.SessionLocal"
        ) as mock_session_local, patch(
            "app.controllers.artist_controller.UserRepository"
        ) as mock_user_repo, patch(
            "app.controllers.artist_controller.UserService"
        ) as mock_user_service:

            mock_session = Mock()
            mock_session_local.return_value = mock_session

            mock_repo_instance = Mock()
            mock_user_repo.return_value = mock_repo_instance

            mock_service_instance = Mock()
            mock_user_service.return_value = mock_service_instance

            result = artist_controller._get_user_service()

            assert result == mock_service_instance
            mock_session_local.assert_called_once()
            mock_user_repo.assert_called_once_with(mock_session)
            mock_user_service.assert_called_once_with(mock_repo_instance)
