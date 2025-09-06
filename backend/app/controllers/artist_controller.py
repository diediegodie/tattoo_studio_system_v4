"""
Artist Controller - SOLID-compliant HTTP route handlers for artist operations.

Following SOLID principles:
- Single Responsibility: Only handles HTTP request/response for artist operations
- Open/Closed: Can be extended without modification
- Dependency Inversion: Depends on service abstractions, not concrete implementations
"""

from flask import Blueprint, request, jsonify, Response
from typing import Dict, Any, Tuple, Union
import logging

from app.services.user_service import UserService
from app.repositories.user_repo import UserRepository
from app.db.session import SessionLocal

# Configure logging
logger = logging.getLogger(__name__)

# Create Blueprint
artist_bp = Blueprint("artist", __name__, url_prefix="/artist")


def _get_user_service() -> UserService:
    """Dependency injection factory for UserService.

    This follows Dependency Inversion Principle by creating the service
    with its required dependencies.
    """
    db_session = SessionLocal()
    user_repo = UserRepository(db_session)
    return UserService(user_repo)


@artist_bp.route("/create", methods=["POST"])
def create_artist():
    """Create a new artist.

    Expected JSON payload:
    {
        "name": "Artist Name",
        "email": "artist@example.com"  // optional
    }

    Returns:
    {
        "success": true,
        "artist": {
            "id": 1,
            "name": "Artist Name",
            "email": "artist@example.com",
            "role": "artist"
        }
    }
    """
    try:
        # Validate request has JSON content
        if not request.is_json:
            return (
                jsonify(
                    {"success": False, "error": "Content-Type must be application/json"}
                ),
                400,
            )

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Request body is required"}), 400

        # Extract and validate required fields
        name = data.get("name")
        if not name or not name.strip():
            return jsonify({"success": False, "error": "Artist name is required"}), 400

        # Extract optional fields
        email = data.get("email")

        # Delegate business logic to service
        user_service = _get_user_service()
        artist = user_service.register_artist(name=name.strip(), email=email)

        # Return success response
        return (
            jsonify(
                {
                    "success": True,
                    "artist": {
                        "id": artist.id,
                        "name": artist.name,
                        "email": artist.email,
                        "role": artist.role,
                    },
                }
            ),
            201,
        )

    except ValueError as e:
        logger.warning(f"Artist creation validation error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 400

    except Exception as e:
        logger.error(f"Unexpected error creating artist: {str(e)}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


@artist_bp.route("/list", methods=["GET"])
def list_artists():
    """Get all artists for dropdowns and selection.

    Returns:
    {
        "success": true,
        "artists": [
            {
                "id": 1,
                "name": "Artist Name",
                "email": "artist@example.com"
            }
        ]
    }
    """
    try:
        # Delegate business logic to service
        user_service = _get_user_service()
        artists = user_service.list_artists()

        # Convert domain entities to API response format
        artists_data = [
            {"id": artist.id, "name": artist.name, "email": artist.email}
            for artist in artists
        ]

        return jsonify({"success": True, "artists": artists_data}), 200

    except Exception as e:
        logger.error(f"Unexpected error listing artists: {str(e)}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


# Form-based endpoint for backwards compatibility
@artist_bp.route("/create_form", methods=["POST"])
def create_artist_form():
    """Create artist from HTML form data.

    This endpoint supports form submissions from the frontend.
    """
    try:
        # Extract form data
        name = request.form.get("name") or request.form.get("artista")
        email = request.form.get("email")

        if not name or not name.strip():
            return jsonify({"success": False, "error": "Artist name is required"}), 400

        # Delegate to service
        user_service = _get_user_service()
        artist = user_service.register_artist(name=name.strip(), email=email)

        # Return JSON response for AJAX calls
        return (
            jsonify(
                {
                    "success": True,
                    "artist": {
                        "id": artist.id,
                        "name": artist.name,
                        "email": artist.email,
                    },
                }
            ),
            201,
        )

    except ValueError as e:
        logger.warning(f"Artist form creation validation error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 400

    except Exception as e:
        logger.error(f"Unexpected error creating artist from form: {str(e)}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


@artist_bp.route("/<int:artist_id>", methods=["GET"])
def get_artist(artist_id: int):
    """Get a specific artist by ID.

    Returns:
    {
        "success": true,
        "artist": {
            "id": 1,
            "name": "Artist Name",
            "email": "artist@example.com"
        }
    }
    """
    try:
        # Delegate business logic to service
        user_service = _get_user_service()
        artist = user_service.repo.get_by_id(artist_id)

        if not artist or artist.role != "artist":
            return jsonify({"success": False, "error": "Artist not found"}), 404

        return (
            jsonify(
                {
                    "success": True,
                    "artist": {
                        "id": artist.id,
                        "name": artist.name,
                        "email": artist.email,
                    },
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Unexpected error getting artist {artist_id}: {str(e)}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


@artist_bp.route("/<int:artist_id>", methods=["PUT"])
def update_artist(artist_id: int):
    """Update an existing artist.

    Expected JSON payload:
    {
        "name": "Updated Artist Name",
        "email": "updated@example.com"  // optional
    }

    Returns:
    {
        "success": true,
        "artist": {
            "id": 1,
            "name": "Updated Artist Name",
            "email": "updated@example.com"
        }
    }
    """
    try:
        # Validate request has JSON content
        if not request.is_json:
            return (
                jsonify(
                    {"success": False, "error": "Content-Type must be application/json"}
                ),
                400,
            )

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "Request body is required"}), 400

        # Extract and validate required fields
        name = data.get("name")
        if not name or not name.strip():
            return jsonify({"success": False, "error": "Artist name is required"}), 400

        # Extract optional fields
        email = data.get("email")

        # Delegate business logic to service
        user_service = _get_user_service()
        artist = user_service.update_artist(
            artist_id=artist_id, name=name.strip(), email=email
        )

        # Return success response
        return (
            jsonify(
                {
                    "success": True,
                    "artist": {
                        "id": artist.id,
                        "name": artist.name,
                        "email": artist.email,
                    },
                }
            ),
            200,
        )

    except ValueError as e:
        logger.warning(f"Artist update validation error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 400

    except Exception as e:
        logger.error(f"Unexpected error updating artist {artist_id}: {str(e)}")
        return jsonify({"success": False, "error": "Internal server error"}), 500


@artist_bp.route("/<int:artist_id>", methods=["DELETE"])
def delete_artist(artist_id: int):
    """Delete an artist by ID.

    Returns:
    {
        "success": true,
        "message": "Artist deleted successfully"
    }
    """
    try:
        # Delegate business logic to service
        user_service = _get_user_service()
        deleted = user_service.delete_artist(artist_id)

        if not deleted:
            return jsonify({"success": False, "error": "Artist not found"}), 404

        return jsonify({"success": True, "message": "Artist deleted successfully"}), 200

    except ValueError as e:
        logger.warning(f"Artist delete validation error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 400

    except Exception as e:
        logger.error(f"Unexpected error deleting artist {artist_id}: {str(e)}")
        return jsonify({"success": False, "error": "Internal server error"}), 500
