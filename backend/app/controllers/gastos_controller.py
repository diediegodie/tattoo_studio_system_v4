import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation

from app.core.api_utils import api_response
from app.db.base import Gasto
from app.db.session import SessionLocal
from app.services.gastos_service import get_gastos_for_month, serialize_gastos
from flask import (Blueprint, flash, jsonify, redirect, render_template,
                   request, url_for)
from flask_login import current_user, login_required
from sqlalchemy.orm import joinedload

logger = logging.getLogger(__name__)


gastos_bp = Blueprint("gastos", __name__, url_prefix="/gastos")


@gastos_bp.route("/", methods=["GET"])
@login_required
def gastos_home():
    db = None
    try:
        db = SessionLocal()
        # Compute start and end of current month
        today = datetime.now()
        start_date = datetime(today.year, today.month, 1)
        if today.month == 12:
            end_date = datetime(today.year + 1, 1, 1)
        else:
            end_date = datetime(today.year, today.month + 1, 1)

        gastos = get_gastos_for_month(db, start_date, end_date)
        gastos_json = serialize_gastos(gastos)

        return render_template("gastos.html", gastos_json=gastos_json)
    except Exception as e:
        logger.exception("Error loading gastos: %s", e)
        flash("Erro ao carregar gastos.", "error")
        return render_template("gastos.html", gastos_json=[])
    finally:
        if db:
            db.close()


@gastos_bp.route("/create", methods=["POST"])
@login_required
def create_gasto():
    db = None
    try:
        db = SessionLocal()

        # Accept form or JSON
        if request.is_json:
            payload = request.get_json(silent=True) or {}
        else:
            payload = request.form.to_dict()

        logger.info("Received payload for gasto creation: %s", payload)

        # Extract fields
        data_str = payload.get("data")
        valor_str = payload.get("valor")
        descricao = (payload.get("descricao") or "").strip()
        forma_pagamento = (payload.get("forma_pagamento") or "").strip()

        # Validate
        errors = []
        try:
            if not data_str:
                errors.append("Data é obrigatória.")
                data_val = None
            else:
                data_val = datetime.strptime(data_str, "%Y-%m-%d").date()
        except Exception:
            errors.append("Data inválida. Use o formato AAAA-MM-DD.")
            data_val = None

        try:
            valor_dec = Decimal(str(valor_str)) if valor_str is not None else None
            if valor_dec is None or valor_dec <= Decimal("0"):
                errors.append("Valor deve ser maior que zero.")
        except (InvalidOperation, TypeError):
            errors.append("Valor inválido.")
            valor_dec = None

        if not descricao:
            errors.append("Descrição é obrigatória.")

        if not forma_pagamento:
            errors.append("Forma de pagamento é obrigatória.")

        logger.info(
            "Validation results: errors=%s, data_val=%s, valor_dec=%s, descricao='%s', forma_pagamento='%s'",
            errors,
            data_val,
            valor_dec,
            descricao,
            forma_pagamento,
        )

        if errors:
            if request.is_json:
                return api_response(False, "; ".join(errors), None, 400)
            for err in errors:
                flash(err, "error")
            return redirect(url_for("gastos.gastos_home"))

        # Ensure current_user is set
        if current_user is None or current_user.id is None:
            logger.error("current_user is None or has no id")
            raise ValueError("User not authenticated")

        logger.info("Creating Gasto with created_by=%s", current_user.id)

        # Create Gasto
        gasto = Gasto(
            data=data_val,
            valor=valor_dec,
            descricao=descricao,
            forma_pagamento=forma_pagamento,
            created_by=current_user.id,
        )

        logger.info("Gasto object created: %s", gasto)

        db.add(gasto)
        logger.info("About to commit gasto to database")
        db.commit()
        logger.info("Gasto committed successfully, refreshing...")
        db.refresh(gasto)
        logger.info("Gasto refreshed: id=%s", gasto.id)

        if request.is_json:
            return api_response(
                True,
                "Gasto registrado com sucesso.",
                {"gasto": serialize_gastos([gasto])[0]},
                201,
            )

        flash("Gasto registrado com sucesso.", "success")
        return redirect(url_for("gastos.gastos_home"))

    except Exception as e:
        if db:
            db.rollback()
        logger.exception("Failed to create gasto: %s", e)
        if request.is_json:
            return api_response(False, f"Erro ao registrar gasto: {str(e)}", None, 500)
        flash("Erro ao registrar gasto.", "error")
        return redirect(url_for("gastos.gastos_home"))
    finally:
        if db:
            db.close()


@gastos_bp.route("/api/<int:gasto_id>", methods=["GET"])
@login_required
def api_get_gasto(gasto_id):
    """Get a single gasto by ID."""
    db = None
    try:
        db = SessionLocal()
        gasto = db.query(Gasto).get(gasto_id)

        if not gasto:
            return api_response(False, "Gasto não encontrado", None, 404)

        # Check if user owns this gasto
        if gasto.created_by != current_user.id:
            return api_response(False, "Acesso negado", None, 403)

        data = {
            "id": gasto.id,
            "data": gasto.data.isoformat() if gasto.data else None,
            "valor": float(gasto.valor) if gasto.valor is not None else None,
            "descricao": gasto.descricao,
            "forma_pagamento": gasto.forma_pagamento,
            "created_at": gasto.created_at.isoformat() if gasto.created_at else None,
        }

        return api_response(True, "Gasto encontrado", data, 200)
    except Exception as e:
        logger.exception("Error in api_get_gasto: %s", e)
        return api_response(False, f"Erro: {str(e)}", None, 500)
    finally:
        if db:
            db.close()


@gastos_bp.route("/api/<int:gasto_id>", methods=["PUT"])
@login_required
def api_update_gasto(gasto_id):
    """Update a gasto by ID via JSON payload."""
    db = None
    try:
        db = SessionLocal()
        gasto = db.query(Gasto).get(gasto_id)
        if not gasto:
            return api_response(False, "Gasto não encontrado", None, 404)

        # Check if user owns this gasto
        if gasto.created_by != current_user.id:
            return api_response(False, "Acesso negado", None, 403)

        payload = request.get_json(force=True, silent=True) or {}

        # Validate required fields
        errors = []
        if "data" in payload and payload.get("data"):
            try:
                gasto.data = datetime.fromisoformat(payload["data"]).date()
            except Exception:
                errors.append("Data inválida")

        if "valor" in payload:
            try:
                gasto.valor = Decimal(str(payload["valor"]))
                if gasto.valor <= 0:
                    errors.append("Valor deve ser maior que zero")
            except Exception:
                errors.append("Valor inválido")

        if "descricao" in payload:
            gasto.descricao = str(payload["descricao"]).strip()
            if not gasto.descricao:
                errors.append("Descrição é obrigatória")

        if "forma_pagamento" in payload:
            gasto.forma_pagamento = str(payload["forma_pagamento"]).strip()
            if not gasto.forma_pagamento:
                errors.append("Forma de pagamento é obrigatória")

        if errors:
            return api_response(False, "; ".join(errors), None, 400)

        db.commit()

        data = {
            "id": gasto.id,
            "data": gasto.data.isoformat() if gasto.data else None,
            "valor": float(gasto.valor) if gasto.valor is not None else None,
            "descricao": gasto.descricao,
            "forma_pagamento": gasto.forma_pagamento,
            "created_at": gasto.created_at.isoformat() if gasto.created_at else None,
        }

        return api_response(True, "Gasto atualizado", data, 200)
    except Exception as e:
        logger.exception("Error updating gasto: %s", e)
        if db:
            db.rollback()
        return api_response(False, f"Erro interno: {str(e)}", None, 500)
    finally:
        if db:
            db.close()


@gastos_bp.route("/api/<int:gasto_id>", methods=["DELETE"])
@login_required
def api_delete_gasto(gasto_id):
    """Delete a gasto by ID."""
    db = None
    try:
        db = SessionLocal()
        gasto = db.query(Gasto).get(gasto_id)
        if not gasto:
            return api_response(False, "Gasto não encontrado", None, 404)

        # Check if user owns this gasto
        if gasto.created_by != current_user.id:
            return api_response(False, "Acesso negado", None, 403)

        db.delete(gasto)
        db.commit()

        return api_response(True, "Gasto excluído", None, 200)
    except Exception as e:
        logger.exception("Error deleting gasto: %s", e)
        if db:
            db.rollback()
        return api_response(False, "Erro interno", None, 500)
    finally:
        if db:
            db.close()
