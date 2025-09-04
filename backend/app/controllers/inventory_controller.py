"""
Inventory controller for handling HTTP requests following SOLID principles.

This controller:
- Handles HTTP concerns only (Single Responsibility)
- Depends on service abstractions (Dependency Inversion)
- Can be easily extended without modification (Open/Closed)
"""

from typing import Optional
from flask import Blueprint, request, jsonify


def api_response(
    success: bool, message: str, data: Optional[dict] = None, status_code: int = 200
):
    return jsonify({"success": success, "message": message, "data": data}), status_code


from flask_login import login_required, current_user
from app.db.session import SessionLocal
from app.repositories.inventory_repository import InventoryRepository
from app.services.inventory_service import InventoryService
from app.domain.entities import InventoryItem

inventory_bp = Blueprint("inventory", __name__, url_prefix="/inventory")


@inventory_bp.route("/", methods=["GET"])
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
@login_required
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
@login_required
def update_inventory(item_id):
    """Update an inventory item."""
    db = SessionLocal()
    try:
        repository = InventoryRepository(db)
        service = InventoryService(repository)
        data = request.get_json()

        existing = service.get_item(item_id)
        if not existing:
            return api_response(False, "Item not found", None, 404)

        updated_item = InventoryItem(
            id=item_id,
            nome=data.get("nome", existing.nome),
            quantidade=data.get("quantidade", existing.quantidade),
            observacoes=data.get("observacoes", existing.observacoes),
        )

        try:
            updated = service.update_item(updated_item)
        except Exception as e:
            return api_response(False, f"Update failed: {str(e)}", None, 400)

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
        return api_response(True, "Item updated successfully", item_data, 200)
    finally:
        db.close()


@inventory_bp.route("/<int:item_id>", methods=["DELETE"])
@login_required
def delete_inventory(item_id):
    """Delete an inventory item."""
    db = SessionLocal()
    try:
        repository = InventoryRepository(db)
        service = InventoryService(repository)

        existing = service.get_item(item_id)
        if not existing:
            return api_response(False, "Item not found", None, 404)

        try:
            service.delete_item(item_id)
        except Exception as e:
            return api_response(False, f"Delete failed: {str(e)}", None, 400)

        return api_response(True, "Item deleted", None, 200)
    finally:
        db.close()


@inventory_bp.route("/<int:item_id>/quantity", methods=["PATCH"])
@login_required
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
            return jsonify({"error": "Item not found"}), 404

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
