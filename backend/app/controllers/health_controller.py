"""
Health controller - health check endpoints for monitoring.
"""

import logging

from app.db.base import Extrato
from app.db.session import SessionLocal
from app.services.extrato_core import get_previous_month
from flask import Blueprint, jsonify

logger = logging.getLogger(__name__)

health_bp = Blueprint("health", __name__, url_prefix="/health")


@health_bp.route("/extrato", methods=["GET"])
def extrato_health_check():
    """
    Check if the extrato snapshot for the previous month exists.

    This endpoint verifies that the monthly extrato generation process
    has completed successfully by checking for the existence of an
    Extrato record for the previous month.

    Returns:
        JSON response with:
        - status: "healthy" if extrato exists, "missing" if not
        - mes: Previous month (1-12)
        - ano: Previous year
        - exists: Boolean indicating if record exists
        - message: Human-readable status message

    Example responses:
        {"status": "healthy", "mes": 9, "ano": 2025, "exists": true, "message": "Extrato for September/2025 exists"}
        {"status": "missing", "mes": 9, "ano": 2025, "exists": false, "message": "Extrato for September/2025 not found"}

    Status codes:
        200: Always (even when extrato is missing, to indicate service is healthy)

    Note:
        - No authentication required (monitoring endpoint)
        - Uses APP_TZ from config for timezone-aware date calculations
        - Includes structured logging for monitoring
    """
    db = None
    try:
        # Get previous month using timezone-aware logic
        mes, ano = get_previous_month()

        logger.info(
            "Health check: checking extrato existence",
            extra={
                "context": {
                    "endpoint": "/health/extrato",
                    "mes": mes,
                    "ano": ano,
                }
            },
        )

        # Query database for extrato record
        db = SessionLocal()
        extrato_record = (
            db.query(Extrato).filter(Extrato.mes == mes, Extrato.ano == ano).first()
        )

        # Determine status
        exists = extrato_record is not None
        status = "healthy" if exists else "missing"

        # Month names for human-readable message
        month_names = {
            1: "January",
            2: "February",
            3: "March",
            4: "April",
            5: "May",
            6: "June",
            7: "July",
            8: "August",
            9: "September",
            10: "October",
            11: "November",
            12: "December",
        }
        month_name = month_names.get(mes, str(mes))
        message = (
            f"Extrato for {month_name}/{ano} {'exists' if exists else 'not found'}"
        )

        # Log result
        logger.info(
            f"Health check result: {status}",
            extra={
                "context": {
                    "endpoint": "/health/extrato",
                    "mes": mes,
                    "ano": ano,
                    "exists": exists,
                    "status": status,
                }
            },
        )

        return (
            jsonify(
                {
                    "status": status,
                    "mes": mes,
                    "ano": ano,
                    "exists": exists,
                    "message": message,
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(
            "Error in extrato health check",
            extra={
                "context": {
                    "endpoint": "/health/extrato",
                    "error": str(e),
                }
            },
            exc_info=True,
        )

        return (
            jsonify(
                {
                    "status": "error",
                    "mes": None,
                    "ano": None,
                    "exists": False,
                    "message": f"Health check failed: {str(e)}",
                }
            ),
            200,  # Still return 200 so monitoring doesn't fail
        )

    finally:
        if db:
            db.close()
