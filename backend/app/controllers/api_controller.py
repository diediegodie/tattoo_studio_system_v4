"""
Example protected routes demonstrating JWT authentication decorators.
These routes show different authentication patterns.
"""

from flask import Blueprint, jsonify, g, request, make_response
from flask_login import logout_user
from flask_login import current_user

from core.auth_decorators import (
    jwt_required,
    jwt_optional,
    login_required_hybrid,
    get_current_user,
)

# Create a blueprint for API routes
api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/logout", methods=["POST"])
def api_logout():
    """Logout endpoint: clears JWT cookie and session."""
    # If using Flask-Login session, log out user
    try:
        logout_user()
    except Exception:
        pass
    # Prepare response to clear JWT cookie
    response = make_response(jsonify({"message": "Logout successful."}))
    response.set_cookie("access_token", "", expires=0)
    return response


@api_bp.route("/profile", methods=["GET"])
@jwt_required
def get_user_profile():
    """Get current user profile (JWT required).

    Example usage:
    curl -H "Authorization: Bearer <token>" http://localhost:5000/api/profile
    """
    user = g.current_user

    return jsonify(
        {
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "avatar_url": user.avatar_url,
                "google_id": user.google_id,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            }
        }
    )


@api_bp.route("/dashboard", methods=["GET"])
@login_required_hybrid
def dashboard():
    """Dashboard that works with both session and JWT auth.

    Can be accessed via:
    1. Web browser with session cookie
    2. API client with JWT token
    """
    user = get_current_user()

    if not user:
        return jsonify({"error": "Authentication required"}), 401

    return jsonify(
        {
            "message": f"Welcome to your dashboard, {user.name}!",
            "user_id": user.id,
            "auth_method": "jwt" if hasattr(g, "current_user") else "session",
        }
    )


@api_bp.route("/public", methods=["GET"])
@jwt_optional
def public_endpoint():
    """Public endpoint with optional authentication.

    Returns different content for authenticated vs anonymous users.
    """
    user = g.current_user

    if user:
        return jsonify(
            {
                "message": f"Hello {user.name}, you are logged in!",
                "authenticated": True,
                "user_id": user.id,
            }
        )
    else:
        return jsonify(
            {
                "message": "Hello anonymous user!",
                "authenticated": False,
                "hint": "Login to see personalized content",
            }
        )


@api_bp.route("/admin", methods=["GET"])
@jwt_required
def admin_only():
    """Example admin-only endpoint.

    In a real app, you'd check user roles/permissions here.
    """
    user = g.current_user

    # Example: Check if user has admin privileges
    # For now, just check if it's a specific email
    if user.email == "admin@tattoo-studio.com":
        return jsonify(
            {
                "message": "Welcome admin!",
                "admin_data": {
                    "total_users": "This would be real admin data",
                    "system_status": "All systems operational",
                },
            }
        )
    else:
        return jsonify({"error": "Forbidden", "message": "Admin access required"}), 403


@api_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint (no auth required)."""
    return jsonify(
        {"status": "healthy", "service": "tattoo-studio-api", "auth": "jwt-ready"}
    )


# Error handlers for the API blueprint
@api_bp.errorhandler(401)
def unauthorized(error):
    """Handle 401 errors with JSON response."""
    return (
        jsonify(
            {
                "error": "Unauthorized",
                "message": "Authentication required to access this resource",
                "status_code": 401,
            }
        ),
        401,
    )


@api_bp.errorhandler(403)
def forbidden(error):
    """Handle 403 errors with JSON response."""
    return (
        jsonify(
            {
                "error": "Forbidden",
                "message": "You do not have permission to access this resource",
                "status_code": 403,
            }
        ),
        403,
    )
