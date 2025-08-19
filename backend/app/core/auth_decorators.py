"""
Authentication decorators and middleware for route protection.
Provides JWT-based authentication for API endpoints.
"""

from functools import wraps
from typing import Optional, Callable, Any
from flask import request, jsonify, g
from flask_login import current_user

from core.security import get_user_from_token
from repositories.user_repo import UserRepository
from db.session import SessionLocal


def jwt_required(f: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to require JWT authentication for a route.

    Checks for JWT token in:
    1. Authorization header (Bearer token)
    2. Cookie (access_token)

    Sets g.current_user if valid token found.
    Returns 401 if no valid token.

    Usage:
        @app.route('/protected')
        @jwt_required
        def protected_route():
            user = g.current_user
            return {'message': f'Hello {user.email}'}
    """

    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        token = None

        # Try to get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        # Fallback to cookie
        if not token:
            token = request.cookies.get("access_token")

        if not token:
            return (
                jsonify(
                    {
                        "error": "Authentication required",
                        "message": "No valid token provided",
                    }
                ),
                401,
            )

        # Validate token and get user info
        user_data = get_user_from_token(token)
        if not user_data:
            return (
                jsonify(
                    {"error": "Invalid token", "message": "Token is expired or invalid"}
                ),
                401,
            )

        # Load full user from database
        db = SessionLocal()
        try:
            repo = UserRepository(db)
            user = repo.get_by_id(user_data["user_id"])

            if not user or not user.is_active:
                return (
                    jsonify(
                        {
                            "error": "User not found",
                            "message": "User account not found or inactive",
                        }
                    ),
                    401,
                )

            # Store user in Flask g object for use in the route
            g.current_user = user

        except Exception as e:
            return (
                jsonify(
                    {"error": "Database error", "message": "Failed to validate user"}
                ),
                500,
            )
        finally:
            db.close()

        return f(*args, **kwargs)

    return decorated_function


def jwt_optional(f: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator for optional JWT authentication.

    Similar to jwt_required but doesn't return 401 if no token.
    Sets g.current_user to None if no valid token.
    Useful for endpoints that work for both authenticated and anonymous users.

    Usage:
        @app.route('/optional-auth')
        @jwt_optional
        def optional_route():
            user = g.current_user
            if user:
                return {'message': f'Hello {user.email}'}
            else:
                return {'message': 'Hello anonymous user'}
    """

    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        token = None
        g.current_user = None

        # Try to get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        # Fallback to cookie
        if not token:
            token = request.cookies.get("access_token")

        if token:
            # Validate token and get user info
            user_data = get_user_from_token(token)
            if user_data:
                # Load full user from database
                db = SessionLocal()
                try:
                    repo = UserRepository(db)
                    user = repo.get_by_id(user_data["user_id"])

                    if user and user.is_active:
                        g.current_user = user

                except Exception:
                    # Silently fail for optional auth
                    pass
                finally:
                    db.close()

        return f(*args, **kwargs)

    return decorated_function


def login_required_hybrid(f: Callable[..., Any]) -> Callable[..., Any]:
    """Hybrid decorator that supports both Flask-Login sessions and JWT tokens.

    Checks for authentication in this order:
    1. Flask-Login session (current_user.is_authenticated)
    2. JWT token (Authorization header or cookie)

    This allows the same route to work with both session-based (web)
    and token-based (API) authentication.

    Usage:
        @app.route('/hybrid-protected')
        @login_required_hybrid
        def hybrid_route():
            # Works with both session and JWT
            if hasattr(g, 'current_user'):
                user = g.current_user  # JWT user
            else:
                user = current_user    # Session user
            return {'message': f'Hello {user.email}'}
    """

    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        # First check Flask-Login session
        if current_user.is_authenticated:
            return f(*args, **kwargs)

        # If no session, try JWT
        token = None

        # Try to get token from Authorization header
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

        # Fallback to cookie
        if not token:
            token = request.cookies.get("access_token")

        if not token:
            # For API requests, return JSON error
            if request.is_json or request.headers.get("Accept", "").startswith(
                "application/json"
            ):
                return (
                    jsonify(
                        {
                            "error": "Authentication required",
                            "message": "Please login to access this resource",
                        }
                    ),
                    401,
                )
            # For web requests, redirect to login
            else:
                from flask import redirect, url_for

                return redirect(url_for("login_page"))

        # Validate JWT token
        user_data = get_user_from_token(token)
        if not user_data:
            if request.is_json or request.headers.get("Accept", "").startswith(
                "application/json"
            ):
                return (
                    jsonify(
                        {
                            "error": "Invalid token",
                            "message": "Token is expired or invalid",
                        }
                    ),
                    401,
                )
            else:
                from flask import redirect, url_for

                return redirect(url_for("login_page"))

        # Load full user from database
        db = SessionLocal()
        try:
            repo = UserRepository(db)
            user = repo.get_by_id(user_data["user_id"])

            if not user or not user.is_active:
                if request.is_json or request.headers.get("Accept", "").startswith(
                    "application/json"
                ):
                    return (
                        jsonify(
                            {
                                "error": "User not found",
                                "message": "User account not found or inactive",
                            }
                        ),
                        401,
                    )
                else:
                    from flask import redirect, url_for

                    return redirect(url_for("login_page"))

            # Store user in Flask g object for JWT-based requests
            g.current_user = user

        except Exception as e:
            if request.is_json or request.headers.get("Accept", "").startswith(
                "application/json"
            ):
                return (
                    jsonify(
                        {
                            "error": "Authentication error",
                            "message": "Failed to validate authentication",
                        }
                    ),
                    500,
                )
            else:
                from flask import redirect, url_for

                return redirect(url_for("login_page"))
        finally:
            db.close()

        return f(*args, **kwargs)

    return decorated_function


def get_current_user():
    """Helper function to get the current user from either JWT or session.

    Returns:
        User object if authenticated, None otherwise

    Usage:
        user = get_current_user()
        if user:
            print(f"Current user: {user.email}")
    """
    # Check JWT user first (stored in g.current_user)
    if hasattr(g, "current_user") and g.current_user:
        return g.current_user

    # Fallback to Flask-Login session user
    if current_user.is_authenticated:
        return current_user

    return None
