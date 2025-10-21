from typing import Dict

from app.core.csrf_config import csrf
from app.core.security import create_user_token
from app.db.session import SessionLocal
from app.repositories.user_repo import UserRepository
from app.services.user_service import UserService
from flask import Blueprint, current_app, jsonify, make_response, request
from flask_login import login_required
from app.core.limiter_config import limiter

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/callback", methods=["POST"])
@csrf.exempt  # JSON API - uses JWT authentication
def auth_callback():
    """Accepts a Google token payload (as JSON) and creates/updates the user.

    Expected JSON body: {"google_info": { ... }} where google_info is the
    userinfo returned from Google (/oauth2/v2/userinfo).
    Returns: JSON with jwt token and user info on success.
    """
    payload = request.get_json(silent=True) or {}
    google_info: Dict = payload.get("google_info") or {}

    if not google_info:
        return jsonify({"error": "missing_google_info"}), 400

    db = SessionLocal()
    try:
        repo = UserRepository(db)
        service = UserService(repo)

        user = service.create_or_update_from_google(google_info)

        # Validate user was created/found with valid ID
        if user is None or user.id is None:
            return (
                jsonify(
                    {
                        "error": "user_creation_failed",
                        "message": "Could not create or find user",
                    }
                ),
                500,
            )

        token = create_user_token(user.id, user.email)

        response = jsonify(
            {
                "token": token,
                "user": {"id": user.id, "email": user.email, "name": user.name},
            }
        )
        # also set cookie for browser flows
        response = make_response(response)

        # Use global cookie config for secure flag (production vs development)
        secure_flag = current_app.config.get("SESSION_COOKIE_SECURE", False)
        response.set_cookie(
            "access_token", token, httponly=True, secure=secure_flag, samesite="Lax"
        )
        return response
    except ValueError as ve:
        return jsonify({"error": "invalid_google_info", "message": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": "server_error", "message": str(e)}), 500
    finally:
        db.close()


@auth_bp.route("/set-password", methods=["POST"])
@limiter.limit("3 per hour")
@csrf.exempt  # JSON API - administrative endpoint
def set_password():
    """Set or reset a local password for a user.

    Expected JSON: {"user_id": int, "password": str}
    Requires a valid user_id and password.
    """
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    password = data.get("password")

    if not user_id or not password:
        return jsonify({"error": "missing_fields"}), 400

    db = SessionLocal()
    try:
        repo = UserRepository(db)
        service = UserService(repo)

        success = service.set_password(int(user_id), password)
        if not success:
            return jsonify({"error": "user_not_found"}), 404

        return jsonify({"message": "password_set"})
    except Exception as e:
        return jsonify({"error": "server_error", "message": str(e)}), 500
    finally:
        db.close()


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("5 per minute;20 per hour")
@csrf.exempt  # JSON API - uses JWT authentication
def local_login():
    """Local email/password login fallback.

    Expected JSON: {"email": str, "password": str}
    Returns JWT token on success.
    """
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "missing_fields"}), 400

    db = SessionLocal()
    try:
        repo = UserRepository(db)
        service = UserService(repo)

        user = service.authenticate_local(email, password)
        if not user:
            return jsonify({"error": "invalid_credentials"}), 401

        token = create_user_token(user.id, user.email)  # type: ignore
        response = jsonify(
            {"token": token, "user": {"id": user.id, "email": user.email}}
        )
        response = make_response(response)

        # Use global cookie config for secure flag (production vs development)
        secure_flag = current_app.config.get("SESSION_COOKIE_SECURE", False)
        response.set_cookie(
            "access_token", token, httponly=True, secure=secure_flag, samesite="Lax"
        )
        return response
    except Exception as e:
        return jsonify({"error": "server_error", "message": str(e)}), 500
    finally:
        db.close()


@auth_bp.route("/logout", methods=["POST"])
@csrf.exempt  # JSON API - uses JWT authentication
@login_required
def logout():
    """Logout the current user and clear JWT/session.

    Returns JSON with success message and clears access_token cookie.
    """
    from flask_login import logout_user

    logout_user()
    response = jsonify({"message": "logout_success"})
    response = make_response(response)

    # Use global cookie config for secure flag (production vs development)
    secure_flag = current_app.config.get("SESSION_COOKIE_SECURE", False)
    response.set_cookie(
        "access_token", "", expires=0, httponly=True, secure=secure_flag, samesite="Lax"
    )
    return response
