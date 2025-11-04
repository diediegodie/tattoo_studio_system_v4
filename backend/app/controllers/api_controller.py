"""
Example protected routes demonstrating JWT authentication decorators.
These routes show different authentication patterns.
"""

import logging
import traceback
from app.core.auth_decorators import get_current_user, jwt_required
from flask import (
    Blueprint,
    g,
    jsonify,
    make_response,
    render_template,
    request,
    current_app,
    abort,
)
from flask_login import current_user, login_required, logout_user
from app.core.csrf_config import csrf
from app.core.limiter_config import limiter

logger = logging.getLogger(__name__)

# Create a blueprint for API routes
api_bp = Blueprint("api", __name__, url_prefix="/api")


@csrf.exempt
@limiter.limit("30 per minute")
@api_bp.route("/logout", methods=["POST"])
def api_logout():
    """Logout endpoint: clears JWT cookie and session."""
    # If using Flask-Login session, log out user
    try:
        logout_user()
    except Exception:
        pass
    # Prepare response to clear JWT cookie
    response = make_response(jsonify({"message": "Logout realizado com sucesso."}))
    secure_flag = current_app.config.get("SESSION_COOKIE_SECURE", False)
    response.set_cookie(
        "access_token",
        "",
        expires=0,
        httponly=True,
        secure=secure_flag,
        samesite="Lax",
    )
    return response


@api_bp.route("/profile", methods=["GET"])
@limiter.limit("100 per minute")
@jwt_required
def get_user_profile():
    """Get current user profile (JWT required).

    Example usage:
    curl -H "Authorization: Bearer <token>" http://localhost:5000/api/profile
    """
    user = get_current_user()

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
@limiter.limit("100 per minute")
@login_required
def dashboard():
    """Dashboard that works with both session and JWT auth.

    Can be accessed via:
    1. Web browser with session cookie
    2. API client with JWT token
    """
    # Using Flask-Login session user
    user = current_user
    if not user or not getattr(user, "is_authenticated", False):
        return jsonify({"error": "Autenticação necessária"}), 401
    return jsonify(
        {
            "message": f"Bem-vindo ao seu painel, {user.name}!",
            "user_id": user.id,
            "auth_method": "session",
        }
    )


@api_bp.route("/public", methods=["GET"])
@limiter.limit("100 per minute")
def public_endpoint():
    """Public endpoint with optional authentication.

    Returns different content for authenticated vs anonymous users.
    """
    # Use Flask-Login's current_user for optional auth
    try:
        user = (
            current_user if getattr(current_user, "is_authenticated", False) else None
        )
    except Exception:
        user = None

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
@login_required
def admin_only():
    """Example admin-only endpoint.

    In a real app, you'd check user roles/permissions here.
    """
    user = current_user

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
        return (
            jsonify(
                {"error": "Proibido", "message": "Acesso de administrador necessário"}
            ),
            403,
        )


@api_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint (no auth required)."""
    return jsonify(
        {"status": "healthy", "service": "tattoo-studio-api", "auth": "jwt-ready"}
    )


@api_bp.route("/internal/health", methods=["GET"])
@limiter.exempt
def internal_health():
    """Internal health check endpoint with token authentication."""
    from app.core.api_utils import verify_health_token
    import logging

    if not verify_health_token():
        abort(401)

    logger = logging.getLogger(__name__)
    logger.info(
        f"Health check authenticated: {request.remote_addr} {request.user_agent}"
    )

    # Basic DB check
    try:
        from app.db.session import SessionLocal
        from sqlalchemy import text

        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Health check DB error: {e}")
        return jsonify({"status": "error", "message": "Database check failed"}), 500

    return jsonify({"status": "ok"}), 200


# Error handlers for the API blueprint
@api_bp.errorhandler(401)
def unauthorized(error):
    """Handle 401 errors with JSON response."""
    return (
        jsonify(
            {
                "error": "Não autorizado",
                "message": "Autenticação necessária para acessar este recurso",
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
                "error": "Proibido",
                "message": "Você não tem permissão para acessar este recurso",
                "status_code": 403,
            }
        ),
        403,
    )


@api_bp.route("/docs", methods=["GET"])
@login_required
def api_docs():
    """API Documentation page."""
    return render_template("api_docs.html")


@csrf.exempt
@limiter.limit("10 per minute")
@api_bp.route("/extrato/generate", methods=["POST"])
@login_required
def generate_extrato_manual():
    """
    Manually trigger extrato generation (admin only).

    This endpoint allows administrators to manually trigger the monthly extrato
    generation process. It uses the atomic transaction function with backup
    verification to ensure data integrity.

    Request body (JSON):
    - month: Month (1-12) - optional, defaults to previous month
    - year: Year (YYYY) - optional, defaults to previous month
    - force: Boolean - whether to force regeneration if extrato already exists

    Returns:
        JSON response with success status and message

    Status codes:
        200: Success
        403: Forbidden (user is not admin)
        400: Bad request (invalid parameters)
        500: Internal server error

    Example:
        POST /api/extrato/generate
        {
            "month": 1,
            "year": 2025,
            "force": false
        }
    """
    # Check if user is admin
    if (
        not current_user.is_authenticated
        or not hasattr(current_user, "role")
        or current_user.role != "admin"
    ):
        logger.warning(
            "Unauthorized extrato generation attempt",
            extra={
                "context": {
                    "job": "manual_extrato_generation",
                    "user_id": getattr(current_user, "id", None),
                    "user_role": getattr(current_user, "role", None),
                    "status": "forbidden",
                }
            },
        )
        return jsonify({"success": False, "error": "Admin access required"}), 403

    try:
        # Parse request body
        data = request.get_json() or {}
        month = data.get("month")
        year = data.get("year")
        force = data.get("force", False)

        # Validate parameters if provided
        if month is not None:
            if not isinstance(month, int) or month < 1 or month > 12:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Month must be an integer between 1 and 12",
                        }
                    ),
                    400,
                )

        if year is not None:
            if not isinstance(year, int) or year < 2000 or year > 2100:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Year must be an integer between 2000 and 2100",
                        }
                    ),
                    400,
                )

        if not isinstance(force, bool):
            return jsonify({"success": False, "error": "Force must be a boolean"}), 400

        # Log the attempt
        logger.info(
            "Manual extrato generation triggered",
            extra={
                "context": {
                    "job": "manual_extrato_generation",
                    "user_id": current_user.id,
                    "user_email": current_user.email,
                    "month": month,
                    "year": year,
                    "force": force,
                    "status": "started",
                }
            },
        )

        # Import and call the atomic function
        from app.services.extrato_atomic import (
            check_and_generate_extrato_with_transaction,
        )

        # Call the atomic function (handles defaults, backup verification, etc.)
        # Note: Function expects mes/ano (Portuguese) but API uses month/year (English)
        success = check_and_generate_extrato_with_transaction(
            mes=month, ano=year, force=force
        )

        if success:
            # Determine actual month/year used (in case defaults were applied)
            if month is None or year is None:
                from app.services.extrato_core import get_previous_month

                actual_month, actual_year = get_previous_month()
            else:
                actual_month, actual_year = month, year

            logger.info(
                "Manual extrato generation completed successfully",
                extra={
                    "context": {
                        "job": "manual_extrato_generation",
                        "user_id": current_user.id,
                        "month": actual_month,
                        "year": actual_year,
                        "force": force,
                        "status": "success",
                    }
                },
            )

            return (
                jsonify(
                    {
                        "success": True,
                        "message": f"Extrato generated successfully for {actual_month:02d}/{actual_year}",
                        "data": {
                            "month": actual_month,
                            "year": actual_year,
                            "force": force,
                        },
                    }
                ),
                200,
            )
        else:
            # Function returned False (could be due to backup failure, existing extrato, etc.)
            logger.error(
                "Manual extrato generation failed",
                extra={
                    "context": {
                        "job": "manual_extrato_generation",
                        "user_id": current_user.id,
                        "month": month,
                        "year": year,
                        "force": force,
                        "status": "failed",
                        "reason": "check_and_generate_extrato_with_transaction returned False",
                    }
                },
            )

            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Extrato generation failed. Check server logs for details.",
                    }
                ),
                500,
            )

    except Exception as e:
        # Handle unexpected errors
        # Safely extract request data for logging (if it exists)
        request_data = request.get_json(silent=True) or {}
        month = request_data.get("month")
        year = request_data.get("year")

        logger.error(
            "Error in manual extrato generation endpoint",
            extra={
                "context": {
                    "job": "manual_extrato_generation",
                    "user_id": current_user.id,
                    "month": month,
                    "year": year,
                    "status": "error",
                    "error_message": str(e),
                }
            },
            exc_info=True,
        )

        return (
            jsonify({"success": False, "error": f"Internal server error: {str(e)}"}),
            500,
        )


@csrf.exempt
@limiter.limit("10 per minute")
@api_bp.route("/backup/create_service", methods=["POST"])
@jwt_required
def create_backup_service():
    """
    Service account endpoint for automated backup creation (JWT-protected).

    This endpoint is designed for automation systems (e.g., GitHub Actions) that
    use JWT Bearer token authentication. It triggers the monthly backup creation
    process for historical data.

    Authentication: Requires valid JWT token in Authorization header (Bearer <token>).
    The token must belong to a service account with admin role (user_id=999).

    Request body (JSON):
    - month: Month (1-12) - optional, defaults to current month
    - year: Year (YYYY) - optional, defaults to current year

    Returns:
        JSON response with success status and message

    Status codes:
        200: Success
        401: Unauthorized (invalid/missing JWT token)
        400: Bad request (invalid parameters)
        409: Backup already exists
        500: Internal server error

    Example:
        POST /api/backup/create_service
        Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
        Content-Type: application/json

        {
            "month": 10,
            "year": 2025
        }
    """
    # Get current user from g (set by @jwt_required decorator)
    user = g.current_user

    try:
        # Parse request body
        data = request.get_json() or {}
        month = data.get("month")
        year = data.get("year")

        # Validate parameters if provided
        if month is not None:
            if not isinstance(month, int) or month < 1 or month > 12:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Month must be an integer between 1 and 12",
                        }
                    ),
                    400,
                )

        if year is not None:
            if not isinstance(year, int) or year < 2000 or year > 2100:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Year must be an integer between 2000 and 2100",
                        }
                    ),
                    400,
                )

        # Log the attempt
        logger.info(
            "Service backup creation triggered",
            extra={
                "context": {
                    "job": "service_backup_creation",
                    "user_id": user.id,
                    "user_email": user.email,
                    "month": month,
                    "year": year,
                    "status": "started",
                }
            },
        )

        # Import and call the backup service
        from app.services.backup_service import BackupService

        # Initialize backup service
        backup_service = BackupService()

        # Create backup
        success, message = backup_service.create_backup(year=year, month=month)

        if success:
            # Determine actual month/year used (in case defaults were applied)
            if month is None or year is None:
                from datetime import datetime

                now = datetime.now()
                actual_month = month or now.month
                actual_year = year or now.year
            else:
                actual_month, actual_year = month, year

            logger.info(
                "Service backup creation completed successfully",
                extra={
                    "context": {
                        "job": "service_backup_creation",
                        "user_id": user.id,
                        "month": actual_month,
                        "year": actual_year,
                        "status": "success",
                    }
                },
            )

            return (
                jsonify(
                    {
                        "success": True,
                        "message": f"Backup created successfully for {actual_month:02d}/{actual_year}",
                        "data": {
                            "month": actual_month,
                            "year": actual_year,
                        },
                    }
                ),
                200,
            )
        else:
            # Determine actual month/year that was attempted
            if month is None or year is None:
                from datetime import datetime

                now = datetime.now()
                actual_month = month or now.month
                actual_year = year or now.year
            else:
                actual_month, actual_year = month, year

            logger.warning(
                "Service backup creation failed",
                extra={
                    "context": {
                        "job": "service_backup_creation",
                        "user_id": user.id,
                        "month": actual_month,
                        "year": actual_year,
                        "status": "failed",
                        "reason": message,
                    }
                },
            )

            # Check if it's a "backup already exists" error
            if "already exists" in message.lower():
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": message,
                            "details": {
                                "month": actual_month,
                                "year": actual_year,
                                "reason": "backup_already_exists",
                            },
                        }
                    ),
                    409,  # Conflict
                )
            else:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": message,
                            "details": {
                                "month": actual_month,
                                "year": actual_year,
                            },
                        }
                    ),
                    500,
                )

    except Exception as e:
        logger.error(
            "Error in service backup creation",
            extra={
                "context": {
                    "job": "service_backup_creation",
                    "user_id": user.id if "user" in locals() else None,
                    "status": "error",
                    "error": str(e),
                }
            },
            exc_info=True,
        )
        return (
            jsonify({"success": False, "error": f"Internal server error: {str(e)}"}),
            500,
        )


@csrf.exempt
@limiter.limit("10 per minute")
@api_bp.route("/extrato/generate_service", methods=["POST"])
@jwt_required
def generate_extrato_service():
    """
    Service account endpoint for automated extrato generation (JWT-protected).

    This endpoint is designed for automation systems (e.g., GitHub Actions) that
    use JWT Bearer token authentication. It triggers the monthly extrato generation
    process using atomic transactions with backup verification.

    Authentication: Requires valid JWT token in Authorization header (Bearer <token>).
    The token must belong to a service account with admin role (user_id=999).

    Request body (JSON):
    - month: Month (1-12) - optional, defaults to previous month
    - year: Year (YYYY) - optional, defaults to previous month
    - force: Boolean - whether to force regeneration if extrato already exists

    Returns:
        JSON response with success status and message

    Status codes:
        200: Success
        401: Unauthorized (invalid/missing JWT token)
        400: Bad request (invalid parameters)
        500: Internal server error

    Example:
        POST /api/extrato/generate_service
        Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
        Content-Type: application/json

        {
            "month": 9,
            "year": 2025,
            "force": false
        }
    """
    # Get current user from g (set by @jwt_required decorator)
    user = g.current_user

    try:
        # Parse request body
        data = request.get_json() or {}
        month = data.get("month")
        year = data.get("year")
        force = data.get("force", False)

        # Validate parameters if provided
        if month is not None:
            if not isinstance(month, int) or month < 1 or month > 12:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Month must be an integer between 1 and 12",
                        }
                    ),
                    400,
                )

        if year is not None:
            if not isinstance(year, int) or year < 2000 or year > 2100:
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Year must be an integer between 2000 and 2100",
                        }
                    ),
                    400,
                )

        if not isinstance(force, bool):
            return jsonify({"success": False, "error": "Force must be a boolean"}), 400

        # Log the attempt
        logger.info(
            "Service extrato generation triggered",
            extra={
                "context": {
                    "job": "service_extrato_generation",
                    "user_id": user.id,
                    "user_email": user.email,
                    "month": month,
                    "year": year,
                    "force": force,
                    "status": "started",
                }
            },
        )

        # Import and call the atomic function
        from app.services.extrato_atomic import (
            check_and_generate_extrato_with_transaction,
            LAST_RUN_INFO,
        )
        from app.services.backup_service import BackupService
        from app.core.config import EXTRATO_REQUIRE_BACKUP

        # Call the atomic function (handles defaults, backup verification, etc.)
        # Note: Function expects mes/ano (Portuguese) but API uses month/year (English)
        success = check_and_generate_extrato_with_transaction(
            mes=month, ano=year, force=force
        )

        if success:
            # Determine actual month/year used (in case defaults were applied)
            if month is None or year is None:
                from app.services.extrato_core import get_previous_month

                actual_month, actual_year = get_previous_month()
            else:
                actual_month, actual_year = month, year

            logger.info(
                "Service extrato generation completed successfully",
                extra={
                    "context": {
                        "job": "service_extrato_generation",
                        "user_id": user.id,
                        "month": actual_month,
                        "year": actual_year,
                        "force": force,
                        "status": "success",
                    }
                },
            )

            return (
                jsonify(
                    {
                        "success": True,
                        "message": f"Extrato generated successfully for {actual_month:02d}/{actual_year}",
                        "data": {
                            "month": actual_month,
                            "year": actual_year,
                            "force": force,
                        },
                    }
                ),
                200,
            )
        else:
            # Function returned False - provide specific diagnostics
            # Determine actual month/year that was attempted
            if month is None or year is None:
                from app.services.extrato_core import get_previous_month

                actual_month, actual_year = get_previous_month()
            else:
                actual_month, actual_year = month, year

            # Check if backup exists to provide specific error message
            backup_service = BackupService()
            backup_exists = backup_service.verify_backup_exists(
                actual_year, actual_month
            )

            if not backup_exists and EXTRATO_REQUIRE_BACKUP:
                # Backup is required but missing
                error_msg = (
                    f"Cannot generate extrato for {actual_month:02d}/{actual_year}: "
                    f"backup verification failed. "
                    f"A backup is required before generating extrato (EXTRATO_REQUIRE_BACKUP=true). "
                    f"Create a backup first or set EXTRATO_REQUIRE_BACKUP=false to bypass this check."
                )
                logger.error(
                    "Service extrato generation failed: backup required but missing",
                    extra={
                        "context": {
                            "job": "service_extrato_generation",
                            "user_id": user.id,
                            "month": actual_month,
                            "year": actual_year,
                            "force": force,
                            "status": "failed",
                            "reason": "backup_verification_failed",
                            "backup_exists": False,
                            "require_backup": True,
                        }
                    },
                )
                return (
                    jsonify(
                        {
                            "success": False,
                            "error": error_msg,
                            "details": {
                                "month": actual_month,
                                "year": actual_year,
                                "backup_exists": False,
                                "backup_required": True,
                            },
                        }
                    ),
                    400,  # Changed to 400 Bad Request - client needs to take action
                )
            else:
                # Other failure reason (existing extrato, no data, etc.)
                logger.error(
                    "Service extrato generation failed",
                    extra={
                        "context": {
                            "job": "service_extrato_generation",
                            "user_id": user.id,
                            "month": actual_month,
                            "year": actual_year,
                            "force": force,
                            "status": "failed",
                            "reason": "check_and_generate_extrato_with_transaction returned False",
                            "correlation_id": LAST_RUN_INFO.get("correlation_id"),
                            "error": LAST_RUN_INFO.get("error"),
                            "stage": LAST_RUN_INFO.get("stage"),
                        }
                    },
                )

                return (
                    jsonify(
                        {
                            "success": False,
                            "error": "Extrato generation failed.",
                            "correlation_id": LAST_RUN_INFO.get("correlation_id"),
                            "stage": LAST_RUN_INFO.get("stage"),
                            "details": LAST_RUN_INFO.get("error"),
                        }
                    ),
                    500,
                )

    except Exception as e:
        # Handle unexpected errors
        # Safely extract request data for logging (if it exists)
        request_data = request.get_json(silent=True) or {}
        month = request_data.get("month")
        year = request_data.get("year")

        logger.error(
            "Error in service extrato generation endpoint",
            extra={
                "context": {
                    "job": "service_extrato_generation",
                    "user_id": user.id,
                    "month": month,
                    "year": year,
                    "status": "error",
                    "error_message": str(e),
                }
            },
            exc_info=True,
        )

        # Temporary: include traceback to speed debugging (remove after fix)
        tb = traceback.format_exc()
        return (
            jsonify(
                {
                    "success": False,
                    "error": f"Internal server error: {str(e)}",
                    "traceback": tb,
                }
            ),
            500,
        )
