"""
Inventory controller for handling HTTP requests following SOLID principles.

This controller:
- Handles HTTP concerns only (Single Responsibility)
- Depends on service abstractions (Dependency Inversion)
- Can be easily extended without modification (Open/Closed)
"""

from typing import Optional

from flask import Blueprint, jsonify, request


def api_response(
    success: bool, message: str, data: Optional[dict] = None, status_code: int = 200
):
    return jsonify({"success": success, "message": message, "data": data}), status_code


from app.core.csrf_config import csrf  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.domain.entities import InventoryItem  # noqa: E402
from app.repositories.inventory_repository import InventoryRepository  # noqa: E402
from app.services.inventory_service import InventoryService  # noqa: E402
from flask_login import login_required  # noqa: E402
from app.core.limiter_config import limiter  # noqa: E402
from app.core.auth_decorators import require_session_authorization  # noqa: E402

inventory_bp = Blueprint("inventory", __name__, url_prefix="/inventory")


@inventory_bp.route("/", methods=["GET"])
@limiter.limit("100 per minute")
@login_required
def list_inventory():
    """List all inventory items."""
    db = SessionLocal()
    try:
        repository = InventoryRepository(db)
        service = InventoryService(repository)
        items = service.list_items()

        return (
            jsonify(
                [
                    {
                        "id": item.id,
                        "nome": item.nome,
                        "quantidade": item.quantidade,
                        "observacoes": item.observacoes,
                        "created_at": (
                            item.created_at.isoformat() if item.created_at else None
                        ),
                        "updated_at": (
                            item.updated_at.isoformat() if item.updated_at else None
                        ),
                    }
                    for item in items
                ]
            ),
            200,
        )
    finally:
        db.close()


@inventory_bp.route("/", methods=["POST"])
@limiter.limit("30 per minute")
@csrf.exempt  # JSON API - uses session authentication
@require_session_authorization
def add_inventory():
    """Add a new inventory item."""
    db = SessionLocal()
    try:
        repository = InventoryRepository(db)
        service = InventoryService(repository)
        # Aceita tanto JSON quanto dados de formulário
        if request.is_json:
            data = request.get_json()
            item = InventoryItem(
                nome=data.get("nome", ""),
                quantidade=int(data.get("quantidade", 0)),
                observacoes=data.get("observacoes", ""),
            )
            created = service.add_item(item)
            return (
                jsonify(
                    {
                        "id": created.id,
                        "nome": created.nome,
                        "quantidade": created.quantidade,
                        "observacoes": created.observacoes,
                        "created_at": (
                            created.created_at.isoformat()
                            if created.created_at
                            else None
                        ),
                        "updated_at": (
                            created.updated_at.isoformat()
                            if created.updated_at
                            else None
                        ),
                    }
                ),
                201,
            )
        else:
            data = request.form
            item = InventoryItem(
                nome=data.get("nome", ""),
                quantidade=int(data.get("quantidade", 0)),
                observacoes=data.get("observacoes", ""),
            )
            created = service.add_item(item)
            from flask import redirect, url_for

            return redirect(url_for("estoque"))
    finally:
        db.close()


@inventory_bp.route("/<int:item_id>", methods=["PUT"])
@limiter.limit("30 per minute")
@csrf.exempt  # JSON API - uses session authentication
@require_session_authorization
def update_inventory(item_id):
    """Update an inventory item."""
    db = SessionLocal()
    try:
        repository = InventoryRepository(db)
        service = InventoryService(repository)
        data = request.get_json()

        existing = service.get_item(item_id)
        if not existing:
            return api_response(False, "Item não encontrado", None, 404)

        updated_item = InventoryItem(
            id=item_id,
            nome=data.get("nome", existing.nome),
            quantidade=data.get("quantidade", existing.quantidade),
            observacoes=data.get("observacoes", existing.observacoes),
        )

        try:
            updated = service.update_item(updated_item)
        except Exception as e:
            return api_response(False, f"Falha na atualização: {str(e)}", None, 400)

        item_data = {
            "id": updated.id,
            "nome": updated.nome,
            "quantidade": updated.quantidade,
            "observacoes": updated.observacoes,
            "created_at": (
                updated.created_at.isoformat() if updated.created_at else None
            ),
            "updated_at": (
                updated.updated_at.isoformat() if updated.updated_at else None
            ),
        }
        return api_response(True, "Item atualizado com sucesso", item_data, 200)
    finally:
        db.close()


@inventory_bp.route("/<int:item_id>", methods=["DELETE"])
@limiter.limit("30 per minute")
@csrf.exempt  # JSON API - uses session authentication
@require_session_authorization
def delete_inventory(item_id):
    """Delete an inventory item."""
    db = SessionLocal()
    try:
        repository = InventoryRepository(db)
        service = InventoryService(repository)

        existing = service.get_item(item_id)
        if not existing:
            return api_response(False, "Item não encontrado", None, 404)

        try:
            service.delete_item(item_id)
        except Exception as e:
            return api_response(False, f"Falha na exclusão: {str(e)}", None, 400)

        return api_response(True, "Item excluído", None, 200)
    finally:
        db.close()


@inventory_bp.route("/<int:item_id>/quantity", methods=["PATCH"])
@limiter.limit("30 per minute")
@csrf.exempt  # JSON API - uses session authentication
@require_session_authorization
def change_quantity(item_id):
    """Change quantity of an inventory item."""
    db = SessionLocal()
    try:
        repository = InventoryRepository(db)
        service = InventoryService(repository)
        data = request.get_json()
        delta = data.get("delta", 0)

        updated = service.change_quantity(item_id, delta)
        if not updated:
            return jsonify({"error": "Item não encontrado"}), 404

        return (
            jsonify(
                {
                    "id": updated.id,
                    "nome": updated.nome,
                    "quantidade": updated.quantidade,
                    "observacoes": updated.observacoes,
                    "created_at": (
                        updated.created_at.isoformat() if updated.created_at else None
                    ),
                    "updated_at": (
                        updated.updated_at.isoformat() if updated.updated_at else None
                    ),
                }
            ),
            200,
        )
    finally:
        db.close()
