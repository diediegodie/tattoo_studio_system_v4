from flask import Blueprint, request, jsonify, make_response
from typing import Dict
from flask_login import login_required

from db.session import SessionLocal
from repositories.user_repo import UserRepository
from services.user_service import UserService
from core.security import create_user_token


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/callback", methods=["POST"])
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

        token = create_user_token(user.id, user.email)  # type: ignore

        response = jsonify(
            {
                "token": token,
                "user": {"id": user.id, "email": user.email, "name": user.name},
            }
        )
        # also set cookie for browser flows
        response = make_response(response)
        response.set_cookie("access_token", token, httponly=True, samesite="Lax")
        return response
    except ValueError as ve:
        return jsonify({"error": "invalid_google_info", "message": str(ve)}), 400
    except Exception as e:
        return jsonify({"error": "server_error", "message": str(e)}), 500
    finally:
        db.close()


@auth_bp.route("/set-password", methods=["POST"])
def set_password():
    """Set or reset a local password for a user.

    Expected JSON: {"user_id": int, "[REDACTED_PASSWORD]"}
    Requires a valid user_id and password.
    """
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id")
    [REDACTED_PASSWORD]"password")

    if not user_id or not [REDACTED_PASSWORD] jsonify({"error": "missing_fields"}), 400

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
def local_login():
    """Local email/password login fallback.

    Expected JSON: {"email": "..", "[REDACTED_PASSWORD]"}
    Returns JWT token on success.
    """
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    [REDACTED_PASSWORD]"password")

    if not email or not [REDACTED_PASSWORD] jsonify({"error": "missing_fields"}), 400

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
        response.set_cookie("access_token", token, httponly=True, samesite="Lax")
        return response
    except Exception as e:
        return jsonify({"error": "server_error", "message": str(e)}), 500
    finally:
        db.close()


@auth_bp.route("/logout", methods=["POST"])
@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """Logout the current user and clear JWT/session.

    Returns JSON with success message and clears access_token cookie.
    """
    from flask_login import logout_user

    logout_user()
    response = jsonify({"message": "logout_success"})
    response = make_response(response)
    response.set_cookie("access_token", "", expires=0, httponly=True, samesite="Lax")
    return response
