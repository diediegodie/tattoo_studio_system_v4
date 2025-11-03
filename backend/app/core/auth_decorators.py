"""
Authentication helpers for this application.

DUAL AUTHENTICATION STRATEGY:
This application uses TWO separate authentication flows:

1. **Human Users (Browser/Frontend):**
   - Authentication: Flask-Login session (OAuth via Google)
   - Authorization: AUTHORIZED_EMAILS environment variable
   - Decorator: @require_session_authorization
   - Use for: All manual user operations (inventory, sessions, payments, etc.)
   - Requires: Active login session + email in authorized list

2. **Automated Systems (GitHub Actions, Scripts):**
   - Authentication: JWT Bearer token
   - Authorization: Service account (user_id=999)
   - Decorator: @jwt_required
   - Use for: Workflow endpoints, API automation
   - Requires: Valid long-lived JWT token

DECORATOR GUIDE:
- @login_required: Use for pages that just need login (HTML views)
- @require_session_authorization: Use for sensitive operations by humans (CRUD, write operations)
- @jwt_required: Use ONLY for automated endpoints (workflow triggers)
- @require_authorization: DEPRECATED - being phased out

Examples:
    # Human user route (browser/frontend)
    @inventory_bp.route('/<int:item_id>/quantity', methods=['PATCH'])
    @require_session_authorization
    def change_quantity(item_id):
        # Uses Flask-Login session + AUTHORIZED_EMAILS
        pass

    # Automated system route (GitHub Actions)
    @api_bp.route('/extrato/generate_service', methods=['POST'])
    @jwt_required
    def generate_extrato_service():
        # Uses JWT Bearer token
        pass
"""

from functools import wraps
from typing import Any

from app.core.security import decode_access_token, get_user_from_token
from flask import g, jsonify, request
from flask_login import current_user


def get_current_user() -> Any:
    """Return current authenticated user, preferring Flask `g.current_user` if set.

    Controllers should prefer `from flask_login import current_user` but this
    helper remains for compatibility with a small number of call sites.
    """
    # Prefer user stored in request-local g (if some adapter set it)
    if hasattr(g, "current_user") and g.current_user:
        return g.current_user

    if current_user and getattr(current_user, "is_authenticated", False):
        return current_user

    return None


def jwt_required(f):
    """Decorator to require JWT authentication for API endpoints.

    Extracts JWT from Authorization header and sets current user.
    If no valid JWT, returns 401.
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        token = auth_header.split(" ")[1]
        payload = decode_access_token(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401

        user_data = get_user_from_token(token)
        if not user_data:
            return jsonify({"error": "Invalid token payload"}), 401

        # For testing purposes, create a mock user object
        # In production, this would fetch from database
        from types import SimpleNamespace

        mock_user = SimpleNamespace()
        mock_user.id = user_data["user_id"]
        mock_user.email = user_data["email"]
        mock_user.name = user_data.get("name", "Test User")
        mock_user.avatar_url = None
        mock_user.google_id = None
        mock_user.is_active = True
        mock_user.created_at = None

        g.current_user = mock_user
        return f(*args, **kwargs)

    return decorated_function


def require_session_authorization(f):
    """Decorator for human users accessing via browser (Flask-Login session + AUTHORIZED_EMAILS).

    This decorator is designed for manual user operations through the web interface.
    It validates:
    1. Flask-Login session is active (user logged in via OAuth)
    2. User's email is in AUTHORIZED_EMAILS list

    Use this for routes accessed by humans through frontend/browser.
    For automated systems (GitHub Actions, scripts), use @jwt_required instead.

    Returns:
        - 401 if not authenticated (no Flask-Login session)
        - 403 if authenticated but email not authorized
        - Proceeds to route if both checks pass

    Usage:
        @inventory_bp.route('/<int:item_id>/quantity', methods=['PATCH'])
        @require_session_authorization
        def change_quantity(item_id):
            # Only authorized logged-in users can access this
            return jsonify({"success": True})
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if login is disabled for testing
        from flask import current_app

        if current_app.config.get("LOGIN_DISABLED", False):
            # In test mode with LOGIN_DISABLED, create a mock authorized user
            from types import SimpleNamespace

            mock_user = SimpleNamespace()
            mock_user.id = 999
            mock_user.email = "test@authorized.com"
            mock_user.name = "Test User"
            g.current_user = mock_user
            return f(*args, **kwargs)

        # Step 1: Check Flask-Login session authentication
        if not current_user or not current_user.is_authenticated:
            return jsonify({"error": "Authentication required. Please log in."}), 401

        # Step 2: Check authorization (email in authorized list)
        from app.core.config import is_email_authorized

        user_email = getattr(current_user, "email", None)
        if not user_email or not is_email_authorized(user_email):
            return (
                jsonify(
                    {
                        "error": "Access denied. Your email is not authorized to access this resource."
                    }
                ),
                403,
            )

        # Authentication and authorization passed - proceed to route
        return f(*args, **kwargs)

    return decorated_function


def require_authorization(f):
    """Decorator to require both authentication AND authorization for sensitive routes.

    ⚠️ DEPRECATED: This decorator is being phased out in favor of:
    - @require_session_authorization for human users (browser/frontend)
    - @jwt_required for automated systems (GitHub Actions, scripts)

    This decorator:
    1. Checks JWT token validity (authentication)
    2. Verifies user email is in authorized list (authorization)

    Returns:
        - 401 if no valid token (authentication failure)
        - 403 if token valid but email not authorized (authorization failure)
        - Proceeds to route if both checks pass

    Usage:
        @app.route('/api/sensitive-data')
        @require_authorization
        def sensitive_endpoint():
            # Only authorized users can access this
            return jsonify({"data": "sensitive"})
    """

    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if login is disabled for testing
        from flask import current_app

        if current_app.config.get("LOGIN_DISABLED", False):
            # In test mode with LOGIN_DISABLED, create a mock authorized user
            from types import SimpleNamespace

            mock_user = SimpleNamespace()
            mock_user.id = 999
            mock_user.email = "test@authorized.com"
            mock_user.name = "Test User"
            g.current_user = mock_user
            return f(*args, **kwargs)

        # Step 1: Check authentication (JWT token)
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401

        token = auth_header.split(" ")[1]
        payload = decode_access_token(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401

        user_data = get_user_from_token(token)
        if not user_data:
            return jsonify({"error": "Invalid token payload"}), 401

        # Step 2: Check authorization (email in authorized list)
        from app.core.config import is_email_authorized

        user_email = user_data.get("email")
        if not user_email or not is_email_authorized(user_email):
            return (
                jsonify(
                    {
                        "error": "Access denied. Your email is not authorized to access this resource."
                    }
                ),
                403,
            )

        # Authentication and authorization passed - set current user
        from types import SimpleNamespace

        mock_user = SimpleNamespace()
        mock_user.id = user_data["user_id"]
        mock_user.email = user_email
        mock_user.name = user_data.get("name", "Test User")
        mock_user.avatar_url = None
        mock_user.google_id = None
        mock_user.is_active = True
        mock_user.created_at = None

        g.current_user = mock_user
        return f(*args, **kwargs)

    return decorated_function
