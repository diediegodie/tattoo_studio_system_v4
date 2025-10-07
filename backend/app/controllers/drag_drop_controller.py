from app.db.session import SessionLocal
from app.repositories.inventory_repository import InventoryRepository
from app.services.inventory_service import InventoryService
from flask import Blueprint, render_template
from flask_login import login_required

drag_drop_bp = Blueprint("drag_drop", __name__)


@drag_drop_bp.route("/drag_drop", methods=["GET", "POST", "PATCH"])
@login_required
def drag_drop():
    from flask import flash, redirect, request, url_for

    if request.method in ["POST", "PATCH"]:
        from flask import jsonify

        if request.is_json:
            data = request.get_json()
            order = data.get("order", [])
            db = SessionLocal()
            try:
                repository = InventoryRepository(db)
                service = InventoryService(repository)
                service.reorder_items(order)
                db.commit()
            except Exception as e:
                db.rollback()
                return jsonify({"success": False, "error": str(e)}), 400
            finally:
                db.close()
            return jsonify({"success": True, "redirect_url": url_for("estoque")})
        else:
            return jsonify({"success": False, "error": "Formato inválido"}), 400
    db = SessionLocal()
    try:
        repository = InventoryRepository(db)
        service = InventoryService(repository)
        inventory_items = service.list_items()
    finally:
        db.close()
    return render_template("drag_drop.html", inventory_items=inventory_items)
