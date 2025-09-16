"""
Admin controller for extrato management operations.

Provides admin-only endpoints for:
- Viewing transfer history
- Manual transfer triggering
- Reverting last transfer
"""

from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import logging
import uuid

from app.db.session import SessionLocal
from app.db.base import ExtratoRunLog, Extrato
from app.services.extrato_atomic import (
    generate_extrato_with_atomic_transaction,
)
from app.services.extrato_core import (
    get_previous_month,
)
from app.services.undo_service import UndoService

logger = logging.getLogger(__name__)

admin_extrato_bp = Blueprint("admin_extrato", __name__, url_prefix="/admin/extrato")


def require_admin():
    """Decorator to check if user is admin."""
    if (
        not current_user.is_authenticated
        or not hasattr(current_user, "role")
        or current_user.role != "admin"
    ):
        return jsonify({"success": False, "message": "Admin access required"}), 403
    return None


@admin_extrato_bp.route("/history", methods=["GET"])
@login_required
def get_transfer_history():
    """
    Get paginated history of extrato transfers.

    Query parameters:
    - page: Page number (default: 1)
    - per_page: Items per page (default: 20, max: 100)
    - status: Filter by status ('success', 'error', 'skipped')
    """
    # Check admin access
    admin_check = require_admin()
    if admin_check:
        return admin_check

    try:
        page = int(request.args.get("page", 1))
        per_page = min(int(request.args.get("per_page", 20)), 100)
        status_filter = request.args.get("status")

        db = SessionLocal()
        try:
            query = db.query(ExtratoRunLog).order_by(ExtratoRunLog.run_at.desc())

            if status_filter:
                query = query.filter(ExtratoRunLog.status == status_filter)

            total = query.count()
            runs = query.offset((page - 1) * per_page).limit(per_page).all()

            result = {
                "success": True,
                "data": {
                    "runs": [
                        {
                            "id": run.id,
                            "mes": run.mes,
                            "ano": run.ano,
                            "run_at": run.run_at.isoformat(),
                            "status": run.status,
                            "message": run.message or "",
                        }
                        for run in runs
                    ],
                    "pagination": {
                        "page": page,
                        "per_page": per_page,
                        "total": total,
                        "pages": (total + per_page - 1) // per_page,
                    },
                },
            }

            logger.info(
                f"Admin {current_user.id} viewed transfer history - page {page}"
            )
            return jsonify(result)

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error retrieving transfer history: {str(e)}")
        return (
            jsonify({"success": False, "message": "Error retrieving transfer history"}),
            500,
        )


@admin_extrato_bp.route("/transfer", methods=["POST"])
@login_required
def trigger_manual_transfer():
    """
    Trigger manual extrato transfer for a specific month/year.

    Request body:
    - mes: Month (1-12) - optional, defaults to previous month
    - ano: Year - optional, defaults to previous month
    - force: Boolean - whether to force overwrite existing extrato
    """
    # Check admin access
    admin_check = require_admin()
    if admin_check:
        return admin_check

    try:
        data = request.get_json() or {}
        mes = data.get("mes")
        ano = data.get("ano")
        force = data.get("force", False)

        # If no month/year specified, use previous month
        if mes is None or ano is None:
            mes, ano = get_previous_month()

        # Validate inputs
        if not isinstance(mes, int) or not isinstance(ano, int):
            return (
                jsonify(
                    {"success": False, "message": "Month and year must be integers"}
                ),
                400,
            )

        if mes < 1 or mes > 12:
            return (
                jsonify(
                    {"success": False, "message": "Month must be between 1 and 12"}
                ),
                400,
            )

        logger.info(
            f"Admin {current_user.id} triggering manual transfer for {mes}/{ano}"
        )

        # Trigger the transfer
        success = generate_extrato_with_atomic_transaction(mes, ano, force=force)

        if success:
            return jsonify(
                {
                    "success": True,
                    "message": f"Extrato transfer completed successfully for {mes}/{ano}",
                    "data": {
                        "mes": mes,
                        "ano": ano,
                        "transferred_at": datetime.now().isoformat(),
                    },
                }
            )
        else:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"Extrato transfer failed for {mes}/{ano}",
                    }
                ),
                500,
            )

    except Exception as e:
        logger.error(f"Error in manual transfer: {str(e)}")
        return (
            jsonify(
                {"success": False, "message": "Internal server error during transfer"}
            ),
            500,
        )


@admin_extrato_bp.route("/revert", methods=["POST"])
@login_required
def revert_last_transfer():
    """
    Revert the last successful extrato transfer using snapshot data.

    Request body:
    - snapshot_id: Optional specific snapshot ID to revert to
    - mes: Month to revert (if not using snapshot_id)
    - ano: Year to revert (if not using snapshot_id)
    """
    # Check admin access
    admin_check = require_admin()
    if admin_check:
        return admin_check

    try:
        data = request.get_json() or {}
        snapshot_id = data.get("snapshot_id")
        mes = data.get("mes")
        ano = data.get("ano")

        logger.info(f"Admin {current_user.id} attempting to revert transfer")

        undo_service = UndoService()

        if snapshot_id:
            # Revert to specific snapshot
            correlation_id = str(uuid.uuid4())[:8]
            success = undo_service.restore_from_snapshot(snapshot_id, correlation_id)
            if success:
                return jsonify(
                    {
                        "success": True,
                        "message": f"Successfully reverted to snapshot {snapshot_id}",
                        "data": {
                            "snapshot_id": snapshot_id,
                            "reverted_at": datetime.now().isoformat(),
                        },
                    }
                )
            else:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": f"Failed to revert to snapshot {snapshot_id}",
                        }
                    ),
                    500,
                )
        else:
            # Find latest snapshot for the specified month/year or last transfer
            if mes and ano:
                snapshots = undo_service.list_snapshots(mes, ano)
            else:
                snapshots = undo_service.list_snapshots()

            if not snapshots:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": "No snapshots found for revert operation",
                        }
                    ),
                    404,
                )

            latest_snapshot = snapshots[0]  # Already ordered by created_at desc
            correlation_id = str(uuid.uuid4())[:8]
            success = undo_service.restore_from_snapshot(
                latest_snapshot["snapshot_id"], correlation_id
            )
            if success:
                return jsonify(
                    {
                        "success": True,
                        "message": f"Successfully reverted to latest snapshot {latest_snapshot['snapshot_id']}",
                        "data": {
                            "snapshot_id": latest_snapshot["snapshot_id"],
                            "mes": latest_snapshot["mes"],
                            "ano": latest_snapshot["ano"],
                            "reverted_at": datetime.now().isoformat(),
                        },
                    }
                )
            else:
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": f"Failed to revert to snapshot {latest_snapshot['snapshot_id']}",
                        }
                    ),
                    500,
                )

    except Exception as e:
        logger.error(f"Error in revert operation: {str(e)}")
        return (
            jsonify(
                {"success": False, "message": "Internal server error during revert"}
            ),
            500,
        )


@admin_extrato_bp.route("/preview", methods=["GET"])
@login_required
def preview_transfer():
    """
    Preview what would be transferred in the monthly extrato process.

    Query parameters:
    - mes: Month (1-12) - optional, defaults to previous month
    - ano: Year - optional, defaults to previous month
    """
    # Check admin access
    admin_check = require_admin()
    if admin_check:
        return admin_check

    try:
        mes = request.args.get("mes", type=int)
        ano = request.args.get("ano", type=int)

        # If no month/year specified, use previous month
        if mes is None or ano is None:
            mes, ano = get_previous_month()

        # Validate inputs
        if mes < 1 or mes > 12:
            return (
                jsonify(
                    {"success": False, "message": "Month must be between 1 and 12"}
                ),
                400,
            )

        db = SessionLocal()
        try:
            # Check if extrato already exists
            existing = (
                db.query(Extrato).filter(Extrato.mes == mes, Extrato.ano == ano).first()
            )

            if existing:
                return jsonify(
                    {
                        "success": True,
                        "data": {
                            "mes": mes,
                            "ano": ano,
                            "status": "already_exists",
                            "existing_extrato_id": existing.id,
                            "message": f"Extrato for {mes}/{ano} already exists",
                        },
                    }
                )

            # Query data that would be transferred
            from app.services.extrato_core import query_data

            pagamentos, sessoes, comissoes, gastos = query_data(db, mes, ano)

            # Calculate totals
            total_pagamentos = len(pagamentos)
            total_sessoes = len(sessoes)
            total_comissoes = len(comissoes)
            total_gastos = len(gastos)

            total_receita = sum(float(getattr(p, "valor", 0)) for p in pagamentos)
            total_comissoes_valor = sum(
                float(getattr(c, "valor", 0)) for c in comissoes
            )
            total_gastos_valor = sum(float(getattr(g, "valor", 0)) for g in gastos)

            preview_data = {
                "mes": mes,
                "ano": ano,
                "status": "ready_for_transfer",
                "counts": {
                    "pagamentos": total_pagamentos,
                    "sessoes": total_sessoes,
                    "comissoes": total_comissoes,
                    "gastos": total_gastos,
                },
                "totals": {
                    "receita": float(total_receita),
                    "comissoes": float(total_comissoes_valor),
                    "gastos": float(total_gastos_valor),
                    "lucro": float(
                        total_receita - total_comissoes_valor - total_gastos_valor
                    ),
                },
            }

            logger.info(f"Admin {current_user.id} previewed transfer for {mes}/{ano}")
            return jsonify({"success": True, "data": preview_data})

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error in transfer preview: {str(e)}")
        return (
            jsonify({"success": False, "message": "Error generating transfer preview"}),
            500,
        )
